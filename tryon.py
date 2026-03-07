"""
OutfitAI — FASHN Virtual Try-On Pipeline
Uses the official FASHN Python SDK with correct API structure.
Docs: https://docs.fashn.ai/sdk/python
"""
import base64
import requests

try:
    from fashn import Fashn
    FASHN_SDK_AVAILABLE = True
except ImportError:
    FASHN_SDK_AVAILABLE = False


class TryOnEngine:
    FASHN_BASE = "https://api.fashn.ai/v1"

    def __init__(self, fashn_api_key: str):
        self.fashn_key = fashn_api_key
        self._headers = {
            "Authorization": f"Bearer {self.fashn_key}",
            "Content-Type": "application/json",
        }

    def _to_data_uri(self, image_bytes: bytes) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        return f"data:image/jpeg;base64,{b64}"

    def _fetch_image(self, url: str):
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            return r.content
        except Exception:
            return None

    def _run_tryon(self, person_bytes: bytes, garment_bytes: bytes, category: str = "auto"):
        """
        Correct FASHN v1.6 API payload:
        {
          "model_name": "tryon-v1.6",
          "inputs": { "model_image": ..., "garment_image": ..., "category": ... }
        }
        Returns (result_bytes, error_string)
        """
        person_uri  = self._to_data_uri(person_bytes)
        garment_uri = self._to_data_uri(garment_bytes)

        # Official SDK path
        if FASHN_SDK_AVAILABLE:
            try:
                client = Fashn(api_key=self.fashn_key)
                result = client.predictions.subscribe(
                    model_name="tryon-v1.6",
                    inputs={
                        "model_image":   person_uri,
                        "garment_image": garment_uri,
                        "category":      category,
                    },
                )
                if result.status != "completed":
                    err = result.error.message if result.error else result.status
                    return None, f"FASHN: {err}"
                output  = result.output
                img_url = output[0] if isinstance(output, list) else output
                data    = self._fetch_image(img_url)
                return (data, None) if data else (None, "Could not download result")
            except Exception as e:
                pass  # fall through to raw REST

        # Raw REST fallback
        import time
        payload = {
            "model_name": "tryon-v1.6",
            "inputs": {
                "model_image":   person_uri,
                "garment_image": garment_uri,
                "category":      category,
            }
        }
        try:
            resp = requests.post(f"{self.FASHN_BASE}/run",
                                 headers=self._headers, json=payload, timeout=30)
            resp.raise_for_status()
            job = resp.json()
        except Exception as e:
            return None, f"FASHN /run failed: {e}"

        pid = job.get("id")
        if not pid:
            return None, f"No prediction ID: {job}"

        for _ in range(40):
            time.sleep(3)
            try:
                poll = requests.get(f"{self.FASHN_BASE}/status/{pid}",
                                    headers=self._headers, timeout=15)
                data = poll.json()
            except Exception:
                continue
            status = data.get("status")
            if status == "completed":
                output  = data.get("output", [])
                img_url = output[0] if isinstance(output, list) and output else output
                if img_url:
                    img = self._fetch_image(img_url)
                    return (img, None) if img else (None, "Download failed")
                return None, "No output URL"
            elif status in ("failed", "cancelled", "time_out"):
                return None, f"Job {status}: {data.get('error','')}"

        return None, "Timeout (120s)"

    def _garment_image(self, item: dict):
        """Return garment bytes: uploaded photo > Unsplash stock."""
        if item.get("uploaded_image"):
            return item["uploaded_image"]
        color = item.get("color", "")
        name  = item.get("name", "clothing")
        query = f"{color}+{name}+fashion+flat+lay".replace(" ", "+")
        try:
            r = requests.get(f"https://source.unsplash.com/400x500/?{query}",
                             timeout=15, allow_redirects=True)
            if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                return r.content
        except Exception:
            pass
        return None

    def run_outfit(self, person_bytes: bytes, outfit_items: list, progress_cb=None) -> dict:
        """
        Chain top → bottom try-ons on the person photo.
        Returns { success, result_image, error, steps }
        """
        result = {"success": False, "result_image": None, "error": None, "steps": []}

        tops    = [i for i in outfit_items if i["category"] == "tops"]
        dresses = [i for i in outfit_items if i["category"] == "dresses"]
        bottoms = [i for i in outfit_items if i["category"] == "bottoms"]

        queue = []
        if dresses:
            queue.append(("full_body", dresses[0]))
        else:
            if tops:    queue.append(("upper_body", tops[0]))
            if bottoms: queue.append(("lower_body", bottoms[0]))

        if not queue:
            result["error"] = "No tops/bottoms/dresses in this outfit"
            return result

        current = person_bytes
        for idx, (cat, item) in enumerate(queue):
            if progress_cb:
                progress_cb(int(10 + idx / len(queue) * 80),
                            f"👗 Trying on {item['color']} {item['name']}...")
            garment = self._garment_image(item)
            if not garment:
                result["error"] = f"No image for {item['name']}"
                return result
            tryon, error = self._run_tryon(current, garment, cat)
            result["steps"].append({"item": item, "success": bool(tryon)})
            if tryon:
                current = tryon
            else:
                result["error"] = error
                return result

        if progress_cb:
            progress_cb(100, "✅ Done!")
        result.update({"success": True, "result_image": current})
        return result
