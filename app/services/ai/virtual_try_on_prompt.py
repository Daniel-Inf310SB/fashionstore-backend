from __future__ import annotations


class VirtualTryOnPrompt:
    """Instrucciones de servidor para transferir una prenda por referencia visual."""

    @staticmethod
    def build() -> str:
        return (
            "TASK: photorealistic virtual garment try-on / garment transfer.\n\n"
            "You receive exactly two images:\n"
            "- IMAGE 1 is the PERSON photo. It is the base image that must be preserved.\n"
            "- IMAGE 2 is the GARMENT REFERENCE. It is the ONLY source of truth for the clothing.\n\n"
            "CRITICAL GARMENT RULES:\n"
            "1. Transfer the exact garment visible in IMAGE 2 onto the person in IMAGE 1.\n"
            "2. Do NOT redesign, reinterpret, replace, simplify, recolor, restyle, or invent the garment.\n"
            "3. Do NOT use catalog metadata, names, color labels, size labels, category labels, brand names, "
            "or any textual assumption to decide what the garment should look like. None of those are authoritative.\n"
            "4. Determine the garment exclusively by visually inspecting IMAGE 2.\n"
            "5. Preserve every visible characteristic from IMAGE 2 as faithfully as possible, including its garment "
            "type, silhouette, dominant and secondary colors, graphics, prints, logos, patterns, neckline, collar, "
            "sleeve presence or absence, sleeve length, straps, buttons, zippers, pockets, seams, trim, hem, texture, "
            "material appearance, proportions, and other visible construction details.\n"
            "6. Never add sleeves, collars, buttons, pockets, patterns, graphics, logos, or other elements that are "
            "not visibly present in IMAGE 2. Never remove visible defining elements from IMAGE 2.\n"
            "7. If a detail is not visible in IMAGE 2, do not creatively redesign it. Infer only the minimum needed "
            "to make the garment wearable while remaining visually consistent with the visible reference.\n\n"
            "PERSON PRESERVATION RULES:\n"
            "1. IMAGE 1 must remain the same person and the same photograph.\n"
            "2. Preserve identity, face, facial features, hair, skin tone, body shape, body proportions, age appearance, "
            "pose, hands, arms, legs, camera angle, crop, background, furniture, lighting, shadows, and environment.\n"
            "3. Do not slim, widen, beautify, reshape, retouch, or otherwise alter the person's body or face.\n"
            "4. Modify only the clothing region needed to replace the person's current garment with IMAGE 2.\n"
            "5. Fit the referenced garment naturally to the existing body and pose using realistic folds, perspective, "
            "occlusion, contact shadows, and fabric deformation without changing its design.\n\n"
            "OUTPUT REQUIREMENT:\n"
            "Return exactly one final photorealistic image: the same person from IMAGE 1 wearing the exact garment "
            "shown in IMAGE 2. The garment reference must remain visually recognizable as that specific item."
        )
