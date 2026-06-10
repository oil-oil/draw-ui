#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 can still use env-based Codex config.
    tomllib = None

DEFAULT_MODEL = os.getenv("DRAW_MODEL", "openai/gpt-image-2")
DEFAULT_PROVIDER = os.getenv("DRAW_PROVIDER", "zenmux")
DEFAULT_BASE_URL = os.getenv("ZENMUX_VERTEX_BASE_URL", "https://zenmux.ai/api/vertex-ai")
DEFAULT_OUTPUT_ROOT = Path.home() / ".local" / "share" / "draw" / "outputs"
DEFAULT_MIME = "image/png"
DEFAULT_CODEX_MODEL = os.getenv("DRAW_CODEX_MODEL", "")




def _read_env_value(path: Path, key: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() != key:
            continue
        value = value.strip().strip('"').strip("'")
        return value
    return ""


def resolve_api_key() -> str:
    env = os.getenv("ZENMUX_API_KEY", "").strip()
    if env:
        return env
    cwd = Path.cwd().resolve()
    for directory in [cwd, *cwd.parents]:
        found = _read_env_value(directory / ".env.local", "ZENMUX_API_KEY")
        if found:
            return found
    config_path = Path.home() / ".config" / "see" / "api_key"
    try:
        return config_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def sanitize_name(value: str, fallback: str = "image") -> str:
    value = value.strip()
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-_.")
    if not value:
        return fallback
    return value[:80]


def build_output_path(*, output_arg: str, image_type: str, topic: str, explicit_name: str, ext: str) -> Path:
    if output_arg:
        out = Path(output_arg).expanduser().resolve()
        if out.suffix:
            return out
        return out.with_suffix(ext)
    now = datetime.now()
    day_dir = DEFAULT_OUTPUT_ROOT / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    base_name = sanitize_name(explicit_name or topic, fallback=image_type)
    return day_dir / f"{now.strftime('%Y%m%d-%H%M%S')}__{image_type}__{base_name}{ext}"


def metadata_path_for(image_path: Path) -> Path:
    return image_path.with_suffix(image_path.suffix + ".json")


def guess_extension(mime_type: str | None) -> str:
    if not mime_type:
        return ".png"
    guessed = mimetypes.guess_extension(mime_type)
    if guessed == ".jpe":
        return ".jpg"
    return guessed or ".png"


# Type only controls aspect ratio, prompt is fully controlled by caller
ASPECT_RATIOS = {
    "ultrawide": "21:9",
    "wide": "16:9",
    "square": "1:1",
    "portrait": "3:4",
    "classic": "4:3",
}

CODEX_SIZE_PRESETS = {
    "ultrawide": "1536x640",
    "wide": "1536x864",
    "classic": "1024x768",
    "square": "1024x1024",
    "portrait": "768x1024",
}

MODE_PROMPTS = {
    "normal": "",
    "replicate": (
        "Use the reference image as the primary visual source. Recreate the UI screen as closely as possible. "
        "Preserve layout, spacing, typography hierarchy, colors, shadows, border radius, icon style, density, "
        "and the relative position of every major element. Do not redesign unless the prompt explicitly asks for changes. "
        "If text is unreadable, preserve its visual length, alignment, and hierarchy. Output only the clean UI mockup, "
        "with no browser chrome, watermark, annotations, or surrounding device frame."
    ),
    "frame-lock": (
        "Use the first reference image as a locked application frame. Preserve the sidebar, top navigation, brand area, "
        "and persistent chrome as closely as possible. Redesign or generate only the content area requested by the prompt. "
        "Keep the result as a clean full-screen UI mockup with no browser chrome or watermark."
    ),
    "asset-redraw": (
        "Use the reference image to recreate only the requested visual asset as a clean standalone asset. Remove surrounding "
        "UI, labels, browser chrome, mockup frames, and unrelated elements unless explicitly requested. Preserve the source "
        "asset's proportions, material, color, and brand feel with high clarity and generous padding."
    ),
}


def effective_prompt(prompt: str, mode: str) -> str:
    mode_prompt = MODE_PROMPTS.get(mode, "")
    if not mode_prompt:
        return prompt
    return f"{mode_prompt}\n\nUser request:\n{prompt}"


def download_file(url: str, dest: Path, timeout: int = 120) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        dest.write_bytes(response.read())


def resolve_ref(raw: str, tmp_dir: Path) -> Path:
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        suffix = Path(parsed.path).suffix or ".png"
        dest = tmp_dir / f"ref-{len(list(tmp_dir.iterdir())) + 1}{suffix}"
        download_file(raw, dest)
        return dest
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Reference not found: {raw}")
    return path


def load_genai():
    try:
        from google import genai
        from google.genai import types
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "[ERROR] Missing dependency `google-genai`. Re-run via scripts/ask_draw.sh so it can auto-install it."
        ) from exc
    return genai, types


def build_contents(*, prompt: str, types, refs: Iterable[Path]):
    parts = [types.Part.from_text(text=prompt)]
    for ref in refs:
        mime = mimetypes.guess_type(ref.name)[0] or DEFAULT_MIME
        parts.append(types.Part.from_bytes(data=ref.read_bytes(), mime_type=mime))
    return parts


def extract_parts(response) -> list:
    if getattr(response, "parts", None):
        return list(response.parts)
    candidates = getattr(response, "candidates", None) or []
    parts = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if content and getattr(content, "parts", None):
            parts.extend(content.parts)
    return parts


def render_response(*, response, output_path: Path) -> tuple[str, str]:
    text_parts: list[str] = []
    image_written = False
    image_mime = DEFAULT_MIME
    pending_bytes: bytes | None = None

    for part in extract_parts(response):
        text = getattr(part, "text", None)
        if text:
            text_parts.append(text.strip())
        inline_data = getattr(part, "inline_data", None)
        if inline_data:
            data = inline_data.data
            if isinstance(data, str):
                pending_bytes = base64.b64decode(data)
            else:
                pending_bytes = data
            image_mime = getattr(inline_data, "mime_type", None) or DEFAULT_MIME

    if pending_bytes:
        final_path = output_path
        if not output_path.suffix:
            final_path = output_path.with_suffix(guess_extension(image_mime))
        final_path.write_bytes(pending_bytes)
        image_written = True
    else:
        final_path = output_path

    if not image_written:
        raise RuntimeError("Model returned no image data.")

    return final_path.as_posix(), "\n".join([t for t in text_parts if t]).strip()


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def load_codex_config() -> dict:
    if tomllib is None:
        return {}
    config_path = codex_home() / "config.toml"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def active_codex_base_url(config: dict) -> str:
    provider_name = config.get("model_provider")
    providers = config.get("model_providers", {})
    if provider_name and isinstance(providers, dict):
        provider = providers.get(provider_name)
        if isinstance(provider, dict):
            base_url = provider.get("base_url")
            if isinstance(base_url, str) and base_url.strip():
                return base_url.strip().rstrip("/")
    return ""


def active_codex_model(config: dict) -> str:
    model = config.get("model")
    if isinstance(model, str) and model.strip():
        return model.strip()
    return ""


def load_codex_api_key() -> str:
    auth_path = codex_home() / "auth.json"
    if not auth_path.exists():
        return ""
    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    key = payload.get("OPENAI_API_KEY")
    return key.strip() if isinstance(key, str) else ""


def resolve_codex_api_key() -> str:
    key = os.getenv("OPENAI_IMAGE_API_KEY") or os.getenv("OPENAI_API_KEY") or load_codex_api_key()
    return key.strip() if key else ""


def resolve_codex_base_url() -> str:
    config = load_codex_config()
    base_url = (
        os.getenv("OPENAI_IMAGE_BASE_URL")
        or active_codex_base_url(config)
        or "https://api.openai.com/v1"
    ).rstrip("/")
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme and parsed.netloc and parsed.path in ("", "/"):
        return f"{base_url}/v1"
    return base_url


def resolve_codex_model() -> str:
    config = load_codex_config()
    return DEFAULT_CODEX_MODEL or active_codex_model(config) or "gpt-5.5"


def join_endpoint(base_url: str, endpoint: str) -> str:
    base = base_url.rstrip("/")
    endpoint = endpoint.lstrip("/")
    if base.endswith("/v1") and endpoint.startswith("v1/"):
        endpoint = endpoint[3:]
    return f"{base}/{endpoint}"


def ref_to_input_image(path: Path) -> dict:
    mime = mimetypes.guess_type(path.name)[0] or DEFAULT_MIME
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "input_image", "image_url": f"data:{mime};base64,{encoded}"}


def looks_like_base64_image(value: str) -> bool:
    if len(value) < 200:
        return False
    compact = value.strip()
    if compact.startswith("data:image/"):
        compact = compact.split(",", 1)[-1]
    try:
        head = base64.b64decode(compact[:256] + "==", validate=False)
    except Exception:
        return False
    return head.startswith(b"\x89PNG") or head.startswith(b"\xff\xd8\xff") or head.startswith(b"RIFF")


def find_image_result_recursive(value: object) -> str | None:
    if isinstance(value, dict):
        value_type = value.get("type")
        for key in ("result", "b64_json", "image_base64"):
            item = value.get(key)
            if isinstance(item, str) and (value_type == "image_generation_call" or looks_like_base64_image(item)):
                return item.split(",", 1)[-1] if item.startswith("data:image/") else item
        for item in value.values():
            found = find_image_result_recursive(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_image_result_recursive(item)
            if found:
                return found
    elif isinstance(value, str) and looks_like_base64_image(value):
        return value.split(",", 1)[-1] if value.startswith("data:image/") else value
    return None


def request_codex_image(*, prompt: str, refs: list[Path], image_type: str, output_path: Path) -> Path:
    api_key = resolve_codex_api_key()
    if not api_key:
        raise RuntimeError("No OPENAI_IMAGE_API_KEY, OPENAI_API_KEY, or Codex auth.json OPENAI_API_KEY found.")

    base_url = resolve_codex_base_url()
    endpoint = join_endpoint(base_url, "responses")
    content: list[dict] = [{"type": "input_text", "text": prompt}]
    content.extend(ref_to_input_image(ref) for ref in refs)
    payload = {
        "model": resolve_codex_model(),
        "instructions": "Use the image_generation tool to create exactly the requested image. Do not add extra text.",
        "stream": False,
        "input": [{"role": "user", "content": content}],
        "tools": [{"type": "image_generation", "size": CODEX_SIZE_PRESETS.get(image_type, "1024x1024")}],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from Codex image API:\n{details}") from exc

    try:
        response_payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Codex image API returned non-JSON response:\n{raw[:1500]}") from exc

    image_b64 = find_image_result_recursive(response_payload)
    if not image_b64:
        raise RuntimeError("No image result found in Codex Responses API output.")

    final_path = output_path if output_path.suffix else output_path.with_suffix(".png")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(base64.b64decode(image_b64))
    return final_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate UI images via ZenMux or a Codex OpenAI-compatible provider.")
    parser.add_argument("--type", choices=sorted(ASPECT_RATIOS.keys()), default="wide", help="Aspect ratio preset.")
    parser.add_argument("--prompt", required=True, help="Full prompt for image generation.")
    parser.add_argument("--ref", action="append", default=[], help="Reference image path or URL (repeatable).")
    parser.add_argument("--name", default="", help="Optional short output name.")
    parser.add_argument("-o", "--output", default="", help="Output image path.")
    parser.add_argument("--provider", choices=["zenmux", "codex"], default=DEFAULT_PROVIDER, help="Image backend.")
    parser.add_argument("--mode", choices=sorted(MODE_PROMPTS.keys()), default="normal", help="UI prompt wrapper.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model override.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=argparse.SUPPRESS)
    return parser.parse_args()


def _uses_generate_images_api(model: str) -> bool:
    """Models that require the generate_images / edit_image API instead of generate_content."""
    return model.startswith("openai/")


def _run_generate_images(*, client, model: str, prompt: str, refs: list[Path], types) -> tuple[bytes, str]:
    """Call generate_images (or edit_image when refs are provided) and return (image_bytes, response_text)."""
    if refs:
        # Use edit_image with reference images
        # First ref becomes the base image
        base_image_path = refs[0]
        base_mime = mimetypes.guess_type(base_image_path.name)[0] or DEFAULT_MIME
        base_image = types.Image(image_bytes=base_image_path.read_bytes(), mime_type=base_mime)
        reference_images = [
            types.RawReferenceImage(reference_id=1, reference_image=base_image)
        ]
        # Additional refs as extra references
        for i, ref_path in enumerate(refs[1:], start=2):
            ref_mime = mimetypes.guess_type(ref_path.name)[0] or DEFAULT_MIME
            ref_img = types.Image(image_bytes=ref_path.read_bytes(), mime_type=ref_mime)
            reference_images.append(
                types.RawReferenceImage(reference_id=i, reference_image=ref_img)
            )
        response = client.models.edit_image(
            model=model,
            prompt=prompt,
            reference_images=reference_images,
        )
    else:
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
        )

    generated = getattr(response, "generated_images", None)
    if not generated:
        raise RuntimeError("Model returned no generated images.")

    image_obj = generated[0].image
    image_bytes = getattr(image_obj, "image_bytes", None)
    if image_bytes is None:
        # Some versions expose .data as base64
        raw = getattr(image_obj, "data", None)
        if isinstance(raw, str):
            image_bytes = base64.b64decode(raw)
        elif isinstance(raw, bytes):
            image_bytes = raw
    if not image_bytes:
        raise RuntimeError("Could not extract image bytes from generate_images response.")

    return image_bytes, ""


def main() -> int:
    args = parse_args()
    aspect_ratio = ASPECT_RATIOS[args.type]
    prompt = effective_prompt(args.prompt, args.mode)

    with tempfile.TemporaryDirectory(prefix="draw-refs-") as tmp:
        tmp_dir = Path(tmp)
        refs = [resolve_ref(raw, tmp_dir) for raw in args.ref]
        output_path = build_output_path(
            output_arg=args.output,
            image_type=args.type,
            topic=args.name or "image",
            explicit_name=args.name,
            ext=".png",
        )

        if args.provider == "codex":
            final_path = request_codex_image(prompt=prompt, refs=refs, image_type=args.type, output_path=output_path)
            response_text = ""
        else:
            api_key = resolve_api_key()
            if not api_key:
                print(
                    "[ERROR] No ZENMUX_API_KEY found. Set it as env var, in .env.local, or in ~/.config/see/api_key",
                    file=sys.stderr,
                )
                return 1

            genai, types = load_genai()
            # OpenAI image models via ZenMux can take longer; bump timeout to 5 minutes.
            timeout = 300 if _uses_generate_images_api(args.model) else 120
            client = genai.Client(
                api_key=api_key,
                vertexai=True,
                http_options=types.HttpOptions(api_version="v1", base_url=args.base_url, timeout=timeout * 1000),
            )

            if _uses_generate_images_api(args.model):
                image_bytes, response_text = _run_generate_images(
                    client=client, model=args.model, prompt=prompt, refs=refs, types=types,
                )
                final_path = output_path if output_path.suffix else output_path.with_suffix(".png")
                final_path.parent.mkdir(parents=True, exist_ok=True)
                final_path.write_bytes(image_bytes)
            else:
                response = client.models.generate_content(
                    model=args.model,
                    contents=build_contents(prompt=prompt, types=types, refs=refs),
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                    ),
                )
                final_path_str, response_text = render_response(response=response, output_path=output_path)
                final_path = Path(final_path_str)

        meta_path = metadata_path_for(final_path)
        metadata = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "type": args.type,
            "aspect_ratio": aspect_ratio,
            "prompt": prompt,
            "raw_prompt": args.prompt,
            "refs": [str(path) for path in refs],
            "provider": args.provider,
            "mode": args.mode,
            "model": args.model if args.provider == "zenmux" else resolve_codex_model(),
            "base_url": args.base_url if args.provider == "zenmux" else resolve_codex_base_url(),
            "output_path": str(final_path),
            "response_text": response_text,
        }
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"output_path={final_path}")
    print(f"metadata_path={meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
