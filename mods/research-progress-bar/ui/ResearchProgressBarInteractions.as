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
            onMarkerMouseOut:Function
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
                onMarkerMouseOut
            );
        }

        public static function clearMarkers(markersContainer:Sprite, tooltipContainer:Sprite):Dictionary {
            ResearchProgressBarTooltipView.hideTooltip(tooltipContainer);
            ResearchProgressBarMarkers.clearMarkers(markersContainer);
            return new Dictionary(true);
        }
    }
}