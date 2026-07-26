package {
    import flash.display.Bitmap;
    import flash.geom.ColorTransform;

    // Recolours the greyscale-on-white marker icons at runtime so each icon takes
    // the colour of its marker's state, matching the dash beneath it. One tint source
    // for both the bar icons and the tooltip icons keeps them in agreement.
    public final class ResearchProgressBarIconTint {
        // Per-state tint colours, sampled from the marker dash PNGs. Because the icons
        // are greyscale-on-white, multiplying by these reproduces the dash's brightest
        // tone on the icon's white areas and scales its shading down from there.
        private static const TINT_COMPLETED:uint = 0xF6F1E7; // marker_white
        private static const TINT_VEHICLE:uint = 0x9CCB68;   // marker_green
        private static const TINT_TOTAL:uint = 0xE4B55A;     // marker_yellow
        private static const TINT_LOCKED:uint = 0x9CA4AB;    // marker_default

        // Canonical colour state of a marker. Mirrors the dot-asset choice in
        // ResearchProgressBarMarkers.createMarkerBitmap so the icon and dot never
        // disagree: markers carry an explicit markerState for most modes, and fall
        // back to the displayed XP readiness (as the dot does) when they do not.
        public static function resolveState(marker:Object, progressValue:Number, combatXp:Number, freeXp:Number):String {
            var markerState:String = marker != null && marker.markerState !== undefined ? String(marker.markerState) : "";

            if (markerState == "completed") {
                return "completed";
            }
            if (markerState == "reachable_vehicle") {
                return "vehicle";
            }
            if (markerState == "reachable_total") {
                return "total";
            }
            if (markerState == "locked") {
                return "locked";
            }
            if (marker != null && marker.isAvailable !== undefined && !Boolean(marker.isAvailable)) {
                return "locked";
            }
            if (progressValue <= combatXp) {
                return "vehicle";
            }
            if (progressValue <= combatXp + freeXp) {
                return "total";
            }
            return "locked";
        }

        public static function colorForState(state:String):uint {
            if (state == "completed") {
                return TINT_COMPLETED;
            }
            if (state == "vehicle") {
                return TINT_VEHICLE;
            }
            if (state == "total") {
                return TINT_TOTAL;
            }
            return TINT_LOCKED;
        }

        public static function colorForMarker(marker:Object, progressValue:Number, combatXp:Number, freeXp:Number):uint {
            return colorForState(resolveState(marker, progressValue, combatXp, freeXp));
        }

        // Tint for a prerequisite reference (item_type/name/xp_cost/is_available from
        // the collector). A missing prerequisite is never "completed", so its colour
        // is its own availability plus XP, the same rule a research marker follows.
        // Without cost data it falls back to the locked grey.
        public static function colorForPrereq(prereq:Object, combatXp:Number, freeXp:Number):uint {
            if (prereq == null || prereq.xp_cost === undefined || prereq.xp_cost == null) {
                return colorForState("locked");
            }
            var available:Boolean = prereq.is_available !== undefined && Boolean(prereq.is_available);
            return colorForState(resolveState({isAvailable: available}, Number(prereq.xp_cost), combatXp, freeXp));
        }

        // Multiply-tints an icon Bitmap in place. The transform is set on the display
        // object, not the embedded BitmapData, so markers that share one embedded asset
        // still tint independently.
        public static function applyColor(icon:Bitmap, color:uint):void {
            if (icon == null) {
                return;
            }

            var transform:ColorTransform = new ColorTransform();
            transform.redMultiplier = ((color >> 16) & 0xFF) / 255.0;
            transform.greenMultiplier = ((color >> 8) & 0xFF) / 255.0;
            transform.blueMultiplier = (color & 0xFF) / 255.0;
            icon.transform.colorTransform = transform;
        }
    }
}
