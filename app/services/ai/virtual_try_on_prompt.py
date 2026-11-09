from __future__ import annotations


class VirtualTryOnPrompt:
    """Instrucciones para transferir una prenda sin alterar ropa ajena a ella."""

    CATEGORY_EDIT_SCOPES = {
        # Parte superior
        "poleras": {
            "profile": "TOP",
            "scope": (
                "Replace ONLY the upper-body top/shirt garment region. "
                "The editable clothing area is the torso and only the sleeves "
                "that belong to that top. Preserve pants, jeans, shorts, skirt, "
                "belt, shoes, legs, and every garment/accessory outside the top."
            ),
        },
        "camisas": {
            "profile": "TOP",
            "scope": (
                "Replace ONLY the upper-body shirt garment region. "
                "The editable clothing area is the torso and only the sleeves "
                "that belong to that shirt. Preserve pants, jeans, shorts, skirt, "
                "belt, shoes, legs, and every garment/accessory outside the shirt."
            ),
        },
        "chaquetas": {
            "profile": "OUTER_TOP",
            "scope": (
                "Replace/add ONLY the upper-body outer-garment region occupied "
                "by the jacket. The jacket may naturally occlude the person's "
                "existing upper garment where the reference jacket covers it, "
                "but do not change any lower-body garment, belt, shoes, or legs."
            ),
        },

        # Prenda completa
        "vestidos": {
            "profile": "DRESS",
            "scope": (
                "Replace ONLY the continuous dress clothing region required by "
                "the reference, from its upper attachment/neckline area through "
                "its visible hem. Preserve face, hair, exposed skin, hands, legs "
                "outside the dress, shoes, accessories, and background."
            ),
        },

        # Parte inferior
        "pantalones": {
            "profile": "BOTTOM_LONG",
            "scope": (
                "Replace ONLY the lower-body trousers/pants garment region from "
                "the waist to the visible trouser hems. Preserve the person's "
                "top/shirt/jacket, torso, arms, face, belt when not part of the "
                "reference, shoes, and all unrelated clothing."
            ),
        },
        "jeans": {
            "profile": "BOTTOM_LONG",
            "scope": (
                "Replace ONLY the lower-body jeans garment region from the waist "
                "to the visible jean hems. Preserve the person's upper-body "
                "garments, torso, arms, face, shoes, and unrelated accessories."
            ),
        },
        "shorts": {
            "profile": "BOTTOM_SHORT",
            "scope": (
                "Replace ONLY the shorts garment region from the waist to the "
                "shorts hem. Preserve the upper-body garments, exposed legs "
                "outside the shorts, shoes, face, body, and background."
            ),
        },
        "faldas": {
            "profile": "SKIRT",
            "scope": (
                "Replace ONLY the skirt garment region from the waist to the "
                "visible skirt hem. Preserve the upper-body garment, exposed "
                "legs outside the skirt, shoes, face, body, and background."
            ),
        },
    }

    @staticmethod
    def resolve_edit_scope(
        category_name: str | None,
    ) -> tuple[str, str]:
        normalized = (category_name or "").strip().casefold()

        config = VirtualTryOnPrompt.CATEGORY_EDIT_SCOPES.get(
            normalized
        )

        if config is not None:
            return config["profile"], config["scope"]

        return (
            "REFERENCE_ONLY",
            (
                "Determine the smallest clothing region that must be edited "
                "from IMAGE 2 itself. Modify ONLY that garment's natural body "
                "region and preserve every other garment, accessory, exposed "
                "body region, and background pixel as much as possible."
            ),
        )

    @staticmethod
    def build(
        *,
        category_name: str | None = None,
    ) -> str:
        profile, scope = VirtualTryOnPrompt.resolve_edit_scope(
            category_name
        )

        return (
            "TASK: photorealistic virtual garment try-on / garment transfer.\n\n"

            "You receive exactly two images:\n"
            "- IMAGE 1 is the PERSON photo. It is the base image that must be preserved.\n"
            "- IMAGE 2 is the GARMENT REFERENCE. It is the ONLY source of truth for how the garment looks.\n\n"

            "EDIT SCOPE CONTROL:\n"
            f"- Garment edit profile: {profile}.\n"
            f"- {scope}\n"
            "- This edit profile is ONLY a spatial/body-region constraint. "
            "It must NEVER be used to invent the garment's design, color, "
            "fabric, silhouette, graphics, length, sleeves, or details.\n"
            "- If IMAGE 2 visually occupies less area than the maximum region "
            "allowed by the edit profile, edit only the smaller visible garment area.\n"
            "- Do not replace all clothing on the person unless the referenced "
            "garment itself genuinely requires that exact area.\n\n"

            "CRITICAL GARMENT RULES:\n"
            "1. Transfer the exact garment visible in IMAGE 2 onto the person in IMAGE 1.\n"
            "2. Do NOT redesign, reinterpret, replace, simplify, recolor, restyle, or invent the garment.\n"
            "3. The category/edit profile may define WHERE editing is allowed, "
            "but it must not define WHAT the garment looks like.\n"
            "4. Determine the garment's visual appearance exclusively by inspecting IMAGE 2.\n"
            "5. Preserve every visible characteristic from IMAGE 2 as faithfully as possible, including its garment "
            "type, silhouette, dominant and secondary colors, graphics, prints, logos, patterns, neckline, collar, "
            "sleeve presence or absence, sleeve length, straps, buttons, zippers, pockets, seams, trim, hem, texture, "
            "material appearance, proportions, and other visible construction details.\n"
            "6. Never add sleeves, collars, buttons, pockets, patterns, graphics, logos, or other elements that are "
            "not visibly present in IMAGE 2. Never remove visible defining elements from IMAGE 2.\n"
            "7. If a detail is not visible in IMAGE 2, infer only the minimum needed to make the garment wearable "
            "while remaining visually consistent with the visible reference.\n\n"

            "NON-TARGET CLOTHING PRESERVATION:\n"
            "1. Clothing outside the target garment region is LOCKED and must remain unchanged.\n"
            "2. Preserve its original color, texture, pattern, shape, length, folds, logos, and accessories.\n"
            "3. Do not coordinate, recolor, redesign, replace, remove, or 'improve' the person's other clothes.\n"
            "4. Natural occlusion is allowed only where the transferred garment physically covers another garment.\n"
            "5. Never alter unrelated clothing merely to make the outfit look more fashionable or coherent.\n\n"

            "PERSON PRESERVATION RULES:\n"
            "1. IMAGE 1 must remain the same person and the same photograph.\n"
            "2. Preserve identity, face, facial features, hair, skin tone, body shape, body proportions, age appearance, "
            "pose, hands, arms, legs, camera angle, crop, background, furniture, lighting, shadows, and environment.\n"
            "3. Do not slim, widen, beautify, reshape, retouch, or otherwise alter the person's body or face.\n"
            "4. Modify only the exact clothing region required by IMAGE 2 and the edit-scope constraints above.\n"
            "5. Fit the referenced garment naturally to the existing body and pose using realistic folds, perspective, "
            "occlusion, contact shadows, and fabric deformation without changing its design.\n\n"

            "OUTPUT REQUIREMENT:\n"
            "Return exactly one final photorealistic image: the same person from IMAGE 1 wearing the exact garment "
            "shown in IMAGE 2, while all non-target clothes remain the same as in IMAGE 1."
        )
