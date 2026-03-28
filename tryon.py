"""
OutfitAI — FASHN Virtual Try-On
Sends base64 images with proper validation + JPEG re-encoding.
"""
import base64, time, io, requests


def _to_jpeg_b64(img_bytes: bytes) -> str:
    """
    Convert any image bytes to a clean JPEG, return as base64 data URI.
    This fixes 400 errors caused by corrupt/wrong-format images from web fetches.
    """
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        # Convert RGBA/P to RGB (JPEG doesn't support alpha)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")
        # Resize if too large (FASHN works best at ~800x1200)
        max_side = 1200
        w, h = img.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        # PIL not available or image broken — send as-is
        b64 = base64.b64encode(img_bytes).decode()
        return f"data:image/jpeg;base64,{b64}"


class TryOnEngine:
    BASE = "https://api.fashn.ai/v1"

    def __init__(self, api_key: str):
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _download(self, url: str):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.content
        except Exception:
            return None

    def tryon(self, person: bytes, garment: bytes, category="auto"):
        """
        Submit try-on job and poll until complete.
        Returns (result_bytes, error_string).
        """
        payload = {
            "model_name": "tryon-v1.6",
            "inputs": {
                "model_image":   _to_jpeg_b64(person),
                "garment_image": _to_jpeg_b64(garment),
                "category":      category,
                "mode":          "balanced",
            }
        }
        try:
            r = requests.post(f"{self.BASE}/run", json=payload,
                              headers=self.headers, timeout=60)
            if not r.ok:
                return None, f"FASHN /run failed: {r.status_code} — {r.text[:300]}"
            job = r.json()
        except Exception as e:
            return None, f"FASHN /run error: {e}"

        pid = job.get("id")
        if not pid:
            return None, f"No prediction ID returned: {job}"

        # Poll up to 120s
        for _ in range(40):
            time.sleep(3)
            try:
                s = requests.get(f"{self.BASE}/status/{pid}",
                                 headers=self.headers, timeout=15).json()
            except Exception:
                continue
            status = s.get("status", "")
            if status == "completed":
                output = s.get("output", [])
                url = output[0] if isinstance(output, list) and output else output
                data = self._download(url)
                return (data, None) if data else (None, "Download failed")
            if status in ("failed", "cancelled", "time_out"):
                err = s.get("error", {})
                return None, f"FASHN job {status}: {err}"

        return None, "Timeout after 120s"

    def run_outfit(self, person: bytes, items: list, progress=None) -> dict:
        """
        Chain try-ons: upper_body first, then lower_body.
        Each item needs: category, name, color, uploaded_image (bytes or None).
        """
        import traceback as _tb

        tops    = [i for i in items if i["category"] == "tops"]
        dresses = [i for i in items if i["category"] == "dresses"]
        bottoms = [i for i in items if i["category"] == "bottoms"]

        queue = []
        if dresses:
            queue.append(("one-pieces", dresses[0]))
        else:
            if tops:    queue.append(("tops",    tops[0]))
            if bottoms: queue.append(("bottoms", bottoms[0]))

        if not queue:
            return {"success": False, "result_image": None,
                    "error": "No tops/bottoms/dresses in outfit"}

        current = person
        for idx, (cat, item) in enumerate(queue):
            if progress:
                try:
                    progress(int(15 + idx / len(queue) * 70),
                             f"👗 Trying on {item['color']} {item['name']}…")
                except Exception:
                    pass

            # Get garment image — prefer uploaded_image, then fetch
            garment = item.get("uploaded_image")
            if not garment:
                try:
                    from garments import get_garment_image
                    garment = get_garment_image(
                        item.get("name", ""), item.get("color", ""), cat)
                except Exception:
                    pass

            if not garment:
                return {"success": False, "result_image": None,
                        "error": f"Could not find garment image for {item['name']}. "
                                 f"Upload a photo of this item in your wardrobe."}

            try:
                result, err = self.tryon(current, garment, cat)
            except Exception as e:
                return {"success": False, "result_image": None,
                        "error": f"tryon() error: {e}\n{_tb.format_exc()}"}

            if result:
                current = result
            else:
                return {"success": False, "result_image": None, "error": err}

        if progress:
            try:
                progress(100, "✅ Done!")
            except Exception:
                pass
        return {"success": True, "result_image": current, "error": None}
