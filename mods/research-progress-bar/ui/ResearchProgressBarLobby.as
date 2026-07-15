package {
    import flash.display.Bitmap;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.events.KeyboardEvent;
    import flash.events.MouseEvent;
    import flash.geom.Matrix;
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
        // Reverse DAAPI channel: when the Python view binds flashObject.script,
        // GFx injects the same-named Python method into this declared slot (the
        // same pattern WG's own meta classes use, e.g. ServerStatsMeta.relogin).
        public var onMarkerClickAction:Function;
        // The marker sprite currently under the cursor (for keyboard picking).
        private var _hoveredMarkerDisplay:Sprite = null;
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
        private var _lastEffectiveScale:Number = -1;

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
            attachKeyListener();
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
            detachKeyListener();
            _hoveredMarkerDisplay = null;
            super.onDispose();
        }

        private function attachKeyListener():void {
            if (stage != null) {
                stage.addEventListener(KeyboardEvent.KEY_DOWN, onStageKeyDown, false, 0, true);
            }
        }

        private function detachKeyListener():void {
            if (stage != null) {
                stage.removeEventListener(KeyboardEvent.KEY_DOWN, onStageKeyDown);
            }
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
            attachKeyListener();
            layoutFromStage();
            stageState = ResearchProgressBarStageSupport.updateTrackedStageSize(stage, _lastStageWidth, _lastStageHeight);
            _lastStageWidth = Number(stageState.stageWidth);
            _lastStageHeight = Number(stageState.stageHeight);
            _lastEffectiveScale = resolveEffectiveScale();
            updateBarFromContext(false);
        }

        private function onEnterFrame(event:Event):void {
            var stageState:Object;
            var scale:Number;

            if (!_isReady || stage == null) {
                return;
            }

            stageState = ResearchProgressBarStageSupport.updateTrackedStageSize(stage, _lastStageWidth, _lastStageHeight);
            scale = resolveEffectiveScale();
            // Interface-scale changes (e.g. x1 -> x2) keep stageWidth/stageHeight
            // constant and only change the inherited scale, so track it explicitly.
            if (!Boolean(stageState.changed) && scale == _lastEffectiveScale) {
                return;
            }

            _lastStageWidth = Number(stageState.stageWidth);
            _lastStageHeight = Number(stageState.stageHeight);
            _lastEffectiveScale = scale;
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
            _lastEffectiveScale = resolveEffectiveScale();
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
                onMarkerMouseOut,
                onMarkerClick
            );
        }

        private function clearMarkers():void {
            _markerTooltipDataByDisplay = ResearchProgressBarInteractions.clearMarkers(
                markersContainer,
                tooltipContainer
            );
        }

        private function onMarkerMouseOver(event:MouseEvent):void {
            _hoveredMarkerDisplay = event != null ? event.currentTarget as Sprite : null;
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
            if (_hoveredMarkerDisplay == (event != null ? event.currentTarget as Sprite : null)) {
                _hoveredMarkerDisplay = null;
            }
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

        // Keyboard pick for a hovered dual marker: WoT's hangar GFx exposes no
        // usable right-click, so the A/B choice is made by key -- 1 (or A) picks
        // Option A, 2 (or B) picks Option B. The chosen modification id rides along
        // as the third argument; WG's own pair dialog then confirms the pick.
        private function onStageKeyDown(event:KeyboardEvent):void {
            var entry:Object;
            var clickAction:Object;
            var code:int;
            var modId:Number;

            if (event == null || _hoveredMarkerDisplay == null || onMarkerClickAction == null) {
                return;
            }
            entry = _markerTooltipDataByDisplay[_hoveredMarkerDisplay];
            if (entry == null || entry.marker == null) {
                return;
            }
            clickAction = entry.marker.clickAction;
            if (clickAction == null || clickAction.leftId === undefined || clickAction.rightId === undefined) {
                return;
            }

            code = event.keyCode;
            modId = Number.NaN;
            if (code == 49 || code == 97 || code == 65) {
                modId = Number(clickAction.leftId);
            }
            else if (code == 50 || code == 98 || code == 66) {
                modId = Number(clickAction.rightId);
            }
            if (!isNaN(modId)) {
                moveFocusToSelf();
                onMarkerClickAction(String(clickAction.kind), Number(clickAction.id), modId);
            }
        }

        // Move focus off any marker to the (persistent) view before an action's
        // modal dialog opens. WG's AbstractView remembers the focused element to
        // restore focus to when the modal resolves; our bar destroys the clicked
        // marker on the post-action sync, so a marker left as the focused element
        // makes AbstractView.onSetModalFocus assert ("Last focused element is not
        // on display list") and corrupts modal focus, taking the hangar's loadout
        // bar down with it. Focusing the view (what AbstractView.draw does itself)
        // keeps _lastFocusedElement valid across the rebuild.
        private function moveFocusToSelf():void {
            try {
                setFocus(this);
            }
            catch (error:Error) {
            }
        }

        private function onMarkerClick(event:MouseEvent):void {
            var markerDisplay:Sprite = event != null ? event.currentTarget as Sprite : null;
            var entry:Object = markerDisplay != null ? _markerTooltipDataByDisplay[markerDisplay] : null;
            var clickAction:Object;

            if (entry == null || entry.marker == null || onMarkerClickAction == null) {
                return;
            }
            if (!ResearchProgressBarInteractions.isMarkerClickable(
                entry.marker,
                Number(entry.combatXp),
                Number(entry.freeXp)
            )) {
                return;
            }

            clickAction = entry.marker.clickAction;
            moveFocusToSelf();
            // Some single-click actions carry a second id (e.g. the modification to
            // switch a picked dual level to); pass it through when present.
            if (clickAction.extra !== undefined) {
                onMarkerClickAction(String(clickAction.kind), Number(clickAction.id), Number(clickAction.extra));
            }
            else {
                onMarkerClickAction(String(clickAction.kind), Number(clickAction.id));
            }
        }

        private function layoutFromStage():void {
            var layout:Object = ResearchProgressBarStageSupport.resolveBarLayout(stage, resolveEffectiveScale());

            x = 0;
            y = 0;
            _barX = Number(layout.barX);
            _barY = Number(layout.barY);
            _barWidth = Number(layout.barWidth);
        }

        // At interface scale x2 the GFx stage is scaled x2 (stage.scaleX == 2) while
        // stage.stageWidth still reports full client pixels, so laying out against the
        // raw stage size doubled the bar's on-screen width and pushed it off both
        // edges. We size against the logical (pre-scale) space instead, derived from
        // this view's own concatenated scale so any scale factor is handled.
        private function resolveEffectiveScale():Number {
            var concat:Matrix = transform.concatenatedMatrix;
            var scale:Number = concat.a;

            if (isNaN(scale) || scale <= 0) {
                return 1;
            }
            return scale;
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

            ResearchProgressBarFonts.setText(separateStatusLabel, nextText);
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
