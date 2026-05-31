package {
    import flash.display.Bitmap;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.events.MouseEvent;
    import flash.text.TextField;
    import flash.utils.Dictionary;
    import net.wg.infrastructure.base.AbstractView;

    [SWF(width="1920", height="220", frameRate="30", backgroundColor="#000000")]
    public class ResearchProgressBarLobby extends AbstractView {
        [Embed(source="assets/progress_bar_base.png")]
        private static const ProgressBarBaseAsset:Class;

        [Embed(source="assets/progress_bar_green.png")]
        private static const ProgressBarGreenAsset:Class;

        [Embed(source="assets/progress_bar_white.png")]
        private static const ProgressBarWhiteAsset:Class;

        [Embed(source="assets/progress_bar_yellow.png")]
        private static const ProgressBarYellowAsset:Class;

        private static const LABEL_COLOR:uint = 0xE6DDC8;
        private static const COUNTER_FONT_SIZE:int = 15;
        private static const COUNTER_FIELD_HEIGHT:Number = 18;
        private static const MARKER_VALUE_COLOR:uint = 0xB8AC97;
        private static const BAR_FILL_MODE_COMPLETED_ONLY:String = "completed_only";
        private static const SEPARATE_STATUS_VERTICAL_GAP:Number = 4;
        private var combatPercentLabel:TextField;
        private var combatPercentCaption:TextField;
        private var totalPercentLabel:TextField;
        private var totalPercentCaption:TextField;
        private var sideCounterLabel:TextField;
        private var sideCounterCaption:TextField;
        private var separateStatusLabel:TextField;
        private var baseBar:Bitmap;
        private var completedBar:Bitmap;
        private var combatBar:Bitmap;
        private var freeBar:Bitmap;
        private var completedMaskShape:Shape;
        private var combatMaskShape:Shape;
        private var freeMaskShape:Shape;
        private var markersContainer:Sprite;
        private var modeButtonsContainer:Sprite;
        private var tooltipContainer:Sprite;
        private var tooltipBackground:Shape;
        private var tooltipContent:Sprite;
        private var _context:Object;
        private var _selectedModeId:String;
        private var _selectedVehicleIntCD:String;
        private var _barX:Number = 0;
        private var _barY:Number = 0;
        private var _barWidth:Number = 0;
        private var _isReady:Boolean = false;
        private var _markerTooltipDataByDisplay:Dictionary = new Dictionary(true);
        private var _modeIdByButton:Dictionary = new Dictionary(true);
        private var _activeCounterLayout:String = "";
        private var _lastStageWidth:Number = -1;
        private var _lastStageHeight:Number = -1;

        public function ResearchProgressBarLobby() {
            super();
        }

        override protected function configUI():void {
            super.configUI();
            visible = false;
            mouseEnabled = false;
            mouseChildren = true;
            build();
            removeEventListener(Event.ENTER_FRAME, onEnterFrame);
            addEventListener(Event.ENTER_FRAME, onEnterFrame, false, 0, true);
            ResearchProgressBarStageSupport.attachListeners(
                stage,
                onStageResize,
                onStageMouseMove,
                onStageMouseLeave
            );
        }

        override protected function onDispose():void {
            ResearchProgressBarTooltipView.hideTooltip(tooltipContainer);
            clearModeButtons();
            removeEventListener(Event.ENTER_FRAME, onEnterFrame);
            ResearchProgressBarStageSupport.detachListeners(
                stage,
                onStageResize,
                onStageMouseMove,
                onStageMouseLeave
            );
            super.onDispose();
        }

        override protected function nextFrameAfterPopulateHandler():void {
            var stageState:Object;

            super.nextFrameAfterPopulateHandler();
            _isReady = true;
            ResearchProgressBarStageSupport.attachListeners(
                stage,
                onStageResize,
                onStageMouseMove,
                onStageMouseLeave
            );
            layoutFromStage();
            stageState = ResearchProgressBarStageSupport.updateTrackedStageSize(stage, _lastStageWidth, _lastStageHeight);
            _lastStageWidth = Number(stageState.stageWidth);
            _lastStageHeight = Number(stageState.stageHeight);
            updateBarFromContext(false);
        }

        private function onEnterFrame(event:Event):void {
            var stageState:Object;

            if (!_isReady || stage == null) {
                return;
            }

            stageState = ResearchProgressBarStageSupport.updateTrackedStageSize(stage, _lastStageWidth, _lastStageHeight);
            if (!Boolean(stageState.changed)) {
                return;
            }

            _lastStageWidth = Number(stageState.stageWidth);
            _lastStageHeight = Number(stageState.stageHeight);
            layoutFromStage();
            updateBarFromContext(false);
        }

        private function build():void {
            var parts:Object = ResearchProgressBarViewFactory.build(
                this,
                ProgressBarBaseAsset,
                ProgressBarWhiteAsset,
                ProgressBarGreenAsset,
                ProgressBarYellowAsset,
                LABEL_COLOR,
                MARKER_VALUE_COLOR,
                COUNTER_FONT_SIZE,
                COUNTER_FIELD_HEIGHT
            );

            combatPercentLabel = parts.combatPercentLabel as TextField;
            combatPercentCaption = parts.combatPercentCaption as TextField;
            totalPercentLabel = parts.totalPercentLabel as TextField;
            totalPercentCaption = parts.totalPercentCaption as TextField;
            sideCounterLabel = parts.sideCounterLabel as TextField;
            sideCounterCaption = parts.sideCounterCaption as TextField;
            separateStatusLabel = parts.separateStatusLabel as TextField;
            baseBar = parts.baseBar as Bitmap;
            completedBar = parts.completedBar as Bitmap;
            combatBar = parts.combatBar as Bitmap;
            freeBar = parts.freeBar as Bitmap;
            completedMaskShape = parts.completedMaskShape as Shape;
            combatMaskShape = parts.combatMaskShape as Shape;
            freeMaskShape = parts.freeMaskShape as Shape;
            markersContainer = parts.markersContainer as Sprite;
            modeButtonsContainer = parts.modeButtonsContainer as Sprite;
            tooltipContainer = parts.tooltipContainer as Sprite;
            tooltipBackground = parts.tooltipBackground as Shape;
            tooltipContent = parts.tooltipContent as Sprite;
        }

        private function onStageResize(event:Event):void {
            layoutFromStage();
            updateBarFromContext(false);
        }

        private function onStageMouseMove(event:MouseEvent):void {
            ResearchProgressBarTooltipView.refreshAtStagePoint(
                visible,
                markersContainer,
                _markerTooltipDataByDisplay,
                tooltipContainer,
                tooltipBackground,
                tooltipContent,
                stage,
                event.stageX,
                event.stageY
            );
        }

        private function onStageMouseLeave(event:Event):void {
            ResearchProgressBarTooltipView.hideTooltip(tooltipContainer);
        }

        public function as_setContext(data:Object):void {
            applyContext(data);
        }

        public function as_ping():String {
            return "research-progress-bar-lobby-ready";
        }

        public function as_getSelectedModeId():String {
            return _selectedModeId;
        }

        public function as_setVisible(value:Boolean):void {
            visible = value;
            if (!value) {
                ResearchProgressBarTooltipView.hideTooltip(tooltipContainer);
            }
        }

        public function as_refreshLayout():void {
            var stageState:Object;

            if (!_isReady) {
                return;
            }

            ResearchProgressBarStageSupport.attachListeners(
                stage,
                onStageResize,
                onStageMouseMove,
                onStageMouseLeave
            );
            layoutFromStage();
            stageState = ResearchProgressBarStageSupport.updateTrackedStageSize(stage, _lastStageWidth, _lastStageHeight);
            _lastStageWidth = Number(stageState.stageWidth);
            _lastStageHeight = Number(stageState.stageHeight);
            updateBarFromContext(false);
        }

        private function applyContext(data:Object):void {
            var nextVehicleIntCD:String = data != null && data.vehicleIntCD !== undefined && data.vehicleIntCD != null
                ? String(data.vehicleIntCD)
                : null;

            if (data == null) {
                return;
            }

            if (_selectedVehicleIntCD != nextVehicleIntCD) {
                _selectedModeId = null;
                _selectedVehicleIntCD = nextVehicleIntCD;
            }

            _context = data;

            if (!_isReady) {
                return;
            }

            updateBarFromContext(false);
        }

        private function updateBarFromContext(relayout:Boolean = true):void {
            var viewState:Object;
            var activeMode:Object;
            var fillState:Object;
            var completedOnly:Boolean;

            if (!_isReady || _context == null) {
                return;
            }

            if (baseBar == null || completedBar == null || combatBar == null || freeBar == null || markersContainer == null || modeButtonsContainer == null) {
                return;
            }

            if (relayout) {
                layoutFromStage();
            }

            viewState = ResearchProgressBarViewState.resolve(
                _context,
                _selectedModeId,
                modeButtonsContainer,
                _barX,
                _barY,
                _barWidth,
                onModeButtonClick,
                BAR_FILL_MODE_COMPLETED_ONLY
            );
            _selectedModeId = viewState.selectedModeId != null
                ? String(viewState.selectedModeId)
                : null;
            _modeIdByButton = viewState.modeIdByButton;

            updateSeparateStatusLabel();

            activeMode = viewState.activeMode;
            if (activeMode == null) {
                clearBarPresentation();
                return;
            }

            _activeCounterLayout = String(viewState.counterState.counterLayout);
            completedOnly = Boolean(viewState.completedOnly);
            fillState = viewState.fillState;

            ResearchProgressBarCounterFields.apply(
                activeMode,
                int(fillState.defaultPrimaryPercent),
                int(fillState.defaultTotalPercent),
                combatPercentLabel,
                combatPercentCaption,
                totalPercentLabel,
                totalPercentCaption,
                sideCounterLabel,
                sideCounterCaption
            );

            markersContainer.visible = true;
            ResearchProgressBarBars.render(
                baseBar,
                completedBar,
                combatBar,
                freeBar,
                completedMaskShape,
                combatMaskShape,
                freeMaskShape,
                _barX,
                _barY,
                _barWidth,
                ResearchProgressBarLayout.BAR_HEIGHT,
                fillState,
                completedOnly
            );

            rebuildMarkers(
                activeMode,
                Number(fillState.barMaxValue),
                Number(fillState.markerPrimaryValue),
                Number(fillState.markerSecondaryValue)
            );
            positionLabels();
        }

        private function clearBarPresentation():void {
            clearMarkers();
            ResearchProgressBarBars.clear(
                baseBar,
                completedBar,
                combatBar,
                freeBar,
                completedMaskShape,
                combatMaskShape,
                freeMaskShape,
                _barX,
                _barY,
                ResearchProgressBarLayout.BAR_HEIGHT
            );
            markersContainer.visible = false;
            combatPercentLabel.text = "";
            combatPercentCaption.text = "";
            totalPercentLabel.text = "";
            totalPercentCaption.text = "";
            sideCounterLabel.text = "";
            sideCounterCaption.text = "";
            _activeCounterLayout = "";
        }

        private function clearModeButtons():void {
            _modeIdByButton = ResearchProgressBarInteractions.clearModeButtons(
                modeButtonsContainer,
                onModeButtonClick
            );
        }

        private function onModeButtonClick(event:MouseEvent):void {
            var modeId:String = ResearchProgressBarInteractions.resolveClickedModeId(
                event,
                _modeIdByButton,
                _selectedModeId
            );

            if (modeId == null) {
                return;
            }

            _selectedModeId = modeId;
            ResearchProgressBarTooltipView.hideTooltip(tooltipContainer);
            updateBarFromContext(false);
        }

        private function rebuildMarkers(activeMode:Object, maxRequirementXp:Number, combatXp:Number, freeXp:Number):void {
            _markerTooltipDataByDisplay = ResearchProgressBarInteractions.rebuildMarkers(
                markersContainer,
                tooltipContainer,
                activeMode,
                maxRequirementXp,
                combatXp,
                freeXp,
                _barWidth,
                _barX,
                _barY,
                onMarkerMouseOver,
                onMarkerMouseOut
            );
        }

        private function clearMarkers():void {
            _markerTooltipDataByDisplay = ResearchProgressBarInteractions.clearMarkers(
                markersContainer,
                tooltipContainer
            );
        }

        private function onMarkerMouseOver(event:MouseEvent):void {
            ResearchProgressBarTooltipView.refreshAtStagePoint(
                visible,
                markersContainer,
                _markerTooltipDataByDisplay,
                tooltipContainer,
                tooltipBackground,
                tooltipContent,
                stage,
                event.stageX,
                event.stageY
            );
        }

        private function onMarkerMouseOut(event:MouseEvent):void {
            ResearchProgressBarTooltipView.refreshAtStagePoint(
                visible,
                markersContainer,
                _markerTooltipDataByDisplay,
                tooltipContainer,
                tooltipBackground,
                tooltipContent,
                stage,
                event.stageX,
                event.stageY
            );
        }

        private function layoutFromStage():void {
            var layout:Object = ResearchProgressBarStageSupport.resolveBarLayout(stage);

            x = 0;
            y = 0;
            _barX = Number(layout.barX);
            _barY = Number(layout.barY);
            _barWidth = Number(layout.barWidth);
        }

        private function positionLabels():void {
            ResearchProgressBarCounterLayout.positionLabels(
                _activeCounterLayout,
                _barX,
                _barY,
                _barWidth,
                ResearchProgressBarLayout.BAR_HEIGHT,
                combatPercentLabel,
                combatPercentCaption,
                totalPercentLabel,
                totalPercentCaption,
                sideCounterLabel,
                sideCounterCaption
            );
        }

        private function updateSeparateStatusLabel():void {
            var modes:Array;
            var layout:Object;
            var nextText:String = "";

            if (separateStatusLabel == null || _context == null) {
                return;
            }

            if (_context.separateStatusText !== undefined && _context.separateStatusText != null) {
                nextText = String(_context.separateStatusText);
            }

            separateStatusLabel.text = nextText;
            separateStatusLabel.visible = nextText.length > 0;
            if (!separateStatusLabel.visible) {
                return;
            }

            modes = ResearchProgressBarModes.resolveModes(_context);
            layout = ResearchProgressBarModes.resolveModeButtonsLayout(
                modes,
                _barX,
                _barY,
                ResearchProgressBarLayout.BAR_HEIGHT,
                ResearchProgressBarLayout.BAR_MIN_STAGE_SIDE_MARGIN
            );

            separateStatusLabel.visible = true;
            separateStatusLabel.x = Number(layout.x) + Number(layout.width) - separateStatusLabel.width;
            separateStatusLabel.y = Number(layout.y) - separateStatusLabel.height - SEPARATE_STATUS_VERTICAL_GAP;
        }

    }
}
