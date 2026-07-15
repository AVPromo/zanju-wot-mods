package {
    import flash.display.Sprite;
    import flash.events.MouseEvent;
    import flash.utils.Dictionary;

    public final class ResearchProgressBarInteractions {
        public static function clearModeButtons(container:Sprite, clickHandler:Function):Dictionary {
            return ResearchProgressBarModes.clearModeButtons(container, clickHandler);
        }

        public static function resolveClickedModeId(
            event:MouseEvent,
            modeIdByButton:Dictionary,
            selectedModeId:String
        ):String {
            var button:Sprite = event != null ? event.currentTarget as Sprite : null;
            var modeId:String;

            if (button == null || modeIdByButton == null) {
                return null;
            }

            modeId = modeIdByButton[button];
            if (modeId == null || modeId == selectedModeId) {
                return null;
            }

            return modeId;
        }

        // Mirrors the tooltip's progress rows: a marker is clickable exactly when a
        // displayed row reads "ready for research" (the Total XP row only exists
        // while singleProgressRow is off, i.e. the Show Total XP setting is on) and
        // Python attached a click action (available, real, directly researchable).
        // Completed markers only ever carry free actions (the loadout-switch
        // toggle), so their click needs no XP gating at all.
        public static function isMarkerClickable(marker:Object, combatXp:Number, freeXp:Number):Boolean {
            var markerState:String;
            var costXp:Number;
            var singleProgressRow:Boolean;

            if (marker == null || marker.clickAction === undefined || marker.clickAction == null) {
                return false;
            }

            markerState = marker.markerState !== undefined ? String(marker.markerState) : "";
            if (markerState == "completed") {
                return true;
            }
            if (marker.isAvailable !== undefined && !Boolean(marker.isAvailable)) {
                return false;
            }

            costXp = Number(marker.costXp);
            if (isNaN(costXp)) {
                return false;
            }
            if (costXp <= 0 || combatXp >= costXp) {
                return true;
            }

            singleProgressRow = marker.singleProgressRow !== undefined && Boolean(marker.singleProgressRow);
            return !singleProgressRow && combatXp + freeXp >= costXp;
        }

        public static function rebuildMarkers(
            markersContainer:Sprite,
            tooltipContainer:Sprite,
            activeMode:Object,
            maxRequirementXp:Number,
            combatXp:Number,
            freeXp:Number,
            barWidth:Number,
            barX:Number,
            barY:Number,
            onMarkerMouseOver:Function,
            onMarkerMouseOut:Function,
            onMarkerClick:Function
        ):Dictionary {
            clearMarkers(markersContainer, tooltipContainer);
            return ResearchProgressBarMarkers.rebuildMarkers(
                markersContainer,
                activeMode,
                maxRequirementXp,
                combatXp,
                freeXp,
                barWidth,
                barX,
                barY,
                onMarkerMouseOver,
                onMarkerMouseOut,
                onMarkerClick
            );
        }

        public static function clearMarkers(markersContainer:Sprite, tooltipContainer:Sprite):Dictionary {
            ResearchProgressBarTooltipView.hideTooltip(tooltipContainer);
            ResearchProgressBarMarkers.clearMarkers(markersContainer);
            return new Dictionary(true);
        }
    }
}
