package {
    import flash.display.Sprite;
    import flash.utils.Dictionary;

    public final class ResearchProgressBarViewState {
        public static function resolve(
            context:Object,
            selectedModeId:String,
            modeButtonsContainer:Sprite,
            barX:Number,
            barY:Number,
            barWidth:Number,
            clickHandler:Function,
            completedOnlyFillMode:String
        ):Object {
            var modes:Array = ResearchProgressBarModes.resolveModes(context);
            var resolvedSelectedModeId:String = ResearchProgressBarModes.syncSelectedMode(
                context,
                modes,
                selectedModeId
            );
            var modeIdByButton:Dictionary = ResearchProgressBarModes.rebuildModeButtons(
                modeButtonsContainer,
                modes,
                resolvedSelectedModeId,
                barX,
                barY,
                ResearchProgressBarLayout.BAR_HEIGHT,
                ResearchProgressBarLayout.BAR_MIN_STAGE_SIDE_MARGIN,
                clickHandler
            );
            var activeMode:Object = ResearchProgressBarModes.resolveSelectedMode(modes, resolvedSelectedModeId);
            var counterState:Object = activeMode != null
                ? ResearchProgressBarCounterFields.resolveState(activeMode)
                : null;
            var completedOnly:Boolean = counterState != null
                && String(counterState.barFillMode) == completedOnlyFillMode;

            return {
                selectedModeId: resolvedSelectedModeId,
                modeIdByButton: modeIdByButton,
                activeMode: activeMode,
                counterState: counterState,
                completedOnly: completedOnly,
                fillState: activeMode != null
                    ? ResearchProgressBarFill.resolve(activeMode, context, barWidth, completedOnly)
                    : null
            };
        }
    }
}