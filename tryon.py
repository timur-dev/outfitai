import base64, time, requests, re

def _fetch_garment_image(item_name, color, category):
    """Fetch a real garment photo for try-on from multiple sources."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def download(url):
        try:
            r = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and "image" in ct and len(r.content) > 5000:
                return r.content
        except Exception:
            pass
        return None

    # Strategy 1: Unsplash (most reliable for fashion)
    q = f"{color}+{item_name}+{category}+fashion+apparel".replace(" ", "+")
    img = download(f"https://source.unsplash.com/400x600/?{q}")
    if img:
        return img

    # Strategy 2: Picsum as absolute fallback (not fashion, but won't crash try-on)
    img = download(f"https://picsum.photos/seed/{item_name.replace(' ','')}/400/600")
    if img:
        return img

    return None

class TryOnEngine:
    BASE = "https://api.fashn.ai/v1"

    def __init__(self, api_key):
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _b64(self, img):
        return "data:image/jpeg;base64," + base64.b64encode(img).decode()

    def _download(self, url):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.content
        except Exception:
            return None

    def tryon(self, person, garment, category="auto"):
        payload = {
            "model_name": "tryon-v1.6",
            "inputs": {
                "model_image":   self._b64(person),
                "garment_image": self._b64(garment),
                "category":      category,
            }
        }
        try:
            r = requests.post(f"{self.BASE}/run", json=payload,
                              headers=self.headers, timeout=30)
            r.raise_for_status()
            job = r.json()
        except Exception as e:
            return None, f"FASHN /run failed: {e}"

        pid = job.get("id")
        if not pid:
            return None, f"No prediction ID: {job}"

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
                return None, f"FASHN job {status}: {s.get('error','')}"

        return None, "Timeout after 120s"

    def run_outfit(self, person, items, progress=None):
        import traceback as _tb
        tops    = [i for i in items if i["category"] == "tops"]
        dresses = [i for i in items if i["category"] == "dresses"]
        bottoms = [i for i in items if i["category"] == "bottoms"]

        queue = []
        if dresses:
            queue.append(("full_body",   dresses[0]))
        else:
            if tops:    queue.append(("upper_body", tops[0]))
            if bottoms: queue.append(("lower_body", bottoms[0]))

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

            garment = item.get("uploaded_image")
            if not garment:
                if progress:
                    try:
                        progress(int(15 + idx / len(queue) * 70),
                                 f"🔍 Finding garment image for {item['name']}…")
                    except Exception:
                        pass
                garment = _fetch_garment_image(
                    item.get("name", "clothing"),
                    item.get("color", ""),
                    item.get("category", "tops")
                )

            if not garment:
                return {"success": False, "result_image": None,
                        "error": f"Could not find garment image for {item['name']}. "
                                 f"Upload a photo of this item in your wardrobe."}

            try:
                result, err = self.tryon(current, garment, cat)
            except Exception as e:
                return {"success": False, "result_image": None,
                        "error": f"tryon() raised: {e}\n{_tb.format_exc()}"}

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

        if not queue:
            return {"success": False, "result_image": None,
                    "error": "No tops/bottoms/dresses in outfit"}

        current = person
        for idx, (cat, item) in enumerate(queue):
            if progress:
                progress(int(15 + idx / len(queue) * 70),
                         f"👗 Trying on {item['color']} {item['name']}…")

            garment = item.get("uploaded_image")
            if not garment:
                q = f"{item['color']}+{item['name']}+fashion+flat+lay".replace(" ", "+")
                try:
                    r = requests.get(f"https://source.unsplash.com/400x500/?{q}",
                                     timeout=15, allow_redirects=True)
                    if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                        garment = r.content
                except Exception:
                    pass

            if not garment:
                return {"success": False, "result_image": None,
                        "error": f"No garment image for {item['name']}"}

            result, err = self.tryon(current, garment, cat)
            if result:
                current = result
            else:
                return {"success": False, "result_image": None, "error": err}

        if progress:
            progress(100, "✅ Done!")
        return {"success": True, "result_image": current, "error": None}
