package {
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.Loader;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.events.IOErrorEvent;
    import flash.events.MouseEvent;
    import flash.geom.Rectangle;
    import flash.net.URLRequest;
    import flash.text.TextField;
    import flash.text.TextFieldAutoSize;
    import flash.text.TextFormat;
    import flash.text.TextFormatAlign;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
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

        [Embed(source="assets/marker_default.png")]
        private static const MarkerDefaultAsset:Class;

        [Embed(source="assets/marker_green.png")]
        private static const MarkerGreenAsset:Class;

        [Embed(source="assets/marker_white.png")]
        private static const MarkerWhiteAsset:Class;

        [Embed(source="assets/marker_yellow.png")]
        private static const MarkerYellowAsset:Class;

        [Embed(source="assets/cog.png")]
        private static const T11CogAsset:Class;

        [Embed(source="assets/star.png")]
        private static const T11StarAsset:Class;

        [Embed(source="assets/circle.png")]
        private static const T11MinorUpgradeAsset:Class;

        [Embed(source="assets/rhomb.png")]
        private static const T11MajorUpgradeAsset:Class;

        private static const SIDE_MARGIN:Number = 600;
        private static const TOP_MARGIN:Number = 105;
        private static const BAR_WIDTH_RATIO:Number = 0.375;
        private static const BAR_DEFAULT_TOP_RATIO:Number = 0.0875;
        private static const BAR_TOP_GAP_RATIO:Number = 0.0291666667;
        private static const BAR_TOP_GAP_MIN:Number = 20;
        private static const BAR_TOP_GAP_MAX:Number = 36;
        private static const BAR_MIN_STAGE_SIDE_MARGIN:Number = 24;
        private static const BAR_TOP_OVERFLOW:Number = 44;
        private static const BAR_SIDE_SAFE_OFFSET:Number = 15;
        private static const LEFT_COUNTER_OFFSET:Number = 3;
        private static const LAYOUT_DISTANCE_BUCKETS:Array = [
            { minWidth: 2560, verticalDistance: 86, horizontalDistance: 367 },
            { minWidth: 1920, verticalDistance: 55, horizontalDistance: 367 },
            { minWidth: 1600, verticalDistance: 51, horizontalDistance: 271 },
            { minWidth: 0, verticalDistance: 43, horizontalDistance: 271 }
        ];
        private static const MIN_BAR_WIDTH:Number = 80;
        private static const BAR_HEIGHT:Number = 8;
        private static const BAR_ASSEMBLY_ABOVE_HEIGHT:Number = 22;
        private static const BAR_ASSEMBLY_BELOW_HEIGHT:Number = 3;
        private static const BAR_ASSEMBLY_HEIGHT:Number = 33;
        private static const LABEL_COLOR:uint = 0xE6DDC8;
        private static const COUNTER_GAP:Number = 14;
        private static const COUNTER_VALUE_WIDTH:Number = 60;
        private static const COUNTER_TEXT_GAP:Number = 5;
        private static const COUNTER_CAPTION_WIDTH:Number = 110;
        private static const COUNTER_TOP_OFFSET:Number = 5;
        private static const COUNTER_FONT_SIZE:int = 15;
        private static const COUNTER_FIELD_HEIGHT:Number = 18;
        private static const RIGHT_COUNTER_VALUE_OFFSET:Number = 3;
        private static const MODE_BUTTON_Y_OFFSET:Number = 18;
        private static const MODE_BUTTON_GAP:Number = 6;
        private static const MODE_BUTTON_BAR_GAP:Number = 15;
        private static const MODE_BUTTON_HEIGHT:Number = 20;
        private static const MODE_BUTTON_BOTTOM_PADDING:Number = 1;
        private static const MODE_BUTTON_PADDING_X:Number = 10;
        private static const MODE_BUTTON_MIN_WIDTH:Number = 48;
        private static const MODE_BUTTON_TEXT_COLOR:uint = 0xD4CAB8;
        private static const MODE_BUTTON_TEXT_ACTIVE_COLOR:uint = 0xF0CF74;
        private static const MODE_BUTTON_BACKGROUND_COLOR:uint = 0x141414;
        private static const MODE_BUTTON_BACKGROUND_ACTIVE_COLOR:uint = 0x4A3A1F;
        private static const MODE_BUTTON_BORDER_COLOR:uint = 0x6C5B47;
        private static const MODE_BUTTON_BORDER_ACTIVE_COLOR:uint = 0xA48745;
        private static const MARKER_VALUE_COLOR:uint = 0xB8AC97;
        private static const MARKER_ICON_SIZE:Number = 48;
        private static const MARKER_ICON_Y_OFFSET:Number = 7;
        private static const TOOLTIP_BACKGROUND_COLOR:uint = 0x0B0B0B;
        private static const TOOLTIP_BACKGROUND_ALPHA:Number = 0.93;
        private static const TOOLTIP_BORDER_COLOR:uint = 0x7A6954;
        private static const TOOLTIP_TEXT_COLOR:uint = 0xE6DDC8;
        private static const TOOLTIP_MUTED_TEXT_COLOR:uint = 0xB8AC97;
        private static const TOOLTIP_HIGHLIGHT_TEXT_COLOR:uint = 0xF0CF74;
        private static const TOOLTIP_PADDING_X:Number = 8;
        private static const TOOLTIP_PADDING_Y:Number = 6;
        private static const TOOLTIP_PADDING_BOTTOM:Number = 8;
        private static const TOOLTIP_OFFSET_Y:Number = 10;
        private static const TOOLTIP_ICON_SIZE:Number = MARKER_ICON_SIZE;
        private static const TOOLTIP_COMPACT_ICON_SIZE:Number = 32;
        private static const TOOLTIP_ICON_LAYOUT_WIDTH:Number = 18;
        private static const TOOLTIP_ICON_GAP:Number = 6;
        private static const TOOLTIP_ROW_GAP:Number = 3;
        private static const TOOLTIP_COMPACT_ROW_GAP:Number = 1;
        private static const TOOLTIP_SECTION_GAP:Number = 10;
        private static const TOOLTIP_TITLE_SIZE:int = 13;
        private static const TOOLTIP_BODY_SIZE:int = 12;
        private static const TOOLTIP_PROGRESS_LABEL_WIDTH:Number = 68;
        private static const TOOLTIP_PROGRESS_PERCENT_WIDTH:Number = 40;
        private static const TOOLTIP_PROGRESS_GAP:Number = 8;
        private static const COUNTER_LAYOUT_RIGHT_SINGLE:String = "right_single";
        private static const COUNTER_LAYOUT_ELITE_STATUS:String = "elite_status";
        private static const BAR_FILL_MODE_COMPLETED_ONLY:String = "completed_only";
        private static const ELITE_STATUS_WIDTH:Number = 210;
        private static const MARKER_TYPE_NAMES:Object = {
            gun: "Gun",
            turret: "Turret",
            engine: "Engine",
            suspension: "Suspension",
            radio: "Radio",
            vehicle: "Next Vehicle",
            firepower: "Firepower",
            survivability: "Survivability",
            mobility: "Mobility",
            stealth: "Scouting",
            reconnaissance: "Scouting",
            scouting: "Scouting",
            special: "Special Upgrade",
            mechanic: "Mechanic Upgrade",
            mechanics: "Mechanic Upgrade",
            minor_upgrade: "Minor Upgrade",
            major_upgrade: "Major Upgrade",
            unknown: "Research Item"
        };
        private static const MARKER_ICON_PATHS:Object = {
            gun: [
                "../maps/icons/hangar/vehicleMenu/small/research_gun.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_gun.png"
            ],
            turret: [
                "../maps/icons/hangar/vehicleMenu/small/research_turret.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_turret.png"
            ],
            engine: [
                "../maps/icons/hangar/vehicleMenu/small/research_engine.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_engine.png"
            ],
            suspension: [
                "../maps/icons/hangar/vehicleMenu/small/research_track.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_track.png"
            ],
            radio: [
                "../maps/icons/hangar/vehicleMenu/small/research_radio.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_radio.png"
            ],
            vehicle: [
                "../maps/icons/hangar/vehicleMenu/small/research.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research.png"
            ],
            firepower: [
                "../maps/icons/specialization/firepower_filter.png",
                "img://gui/maps/icons/specialization/firepower_filter.png"
            ],
            survivability: [
                "../maps/icons/specialization/survivability_filter.png",
                "img://gui/maps/icons/specialization/survivability_filter.png"
            ],
            mobility: [
                "../maps/icons/specialization/mobility_filter.png",
                "img://gui/maps/icons/specialization/mobility_filter.png"
            ],
            stealth: [
                "../maps/icons/specialization/stealth_filter.png",
                "img://gui/maps/icons/specialization/stealth_filter.png"
            ],
            reconnaissance: [
                "../maps/icons/specialization/stealth_filter.png",
                "img://gui/maps/icons/specialization/stealth_filter.png"
            ],
            scouting: [
                "../maps/icons/specialization/stealth_filter.png",
                "img://gui/maps/icons/specialization/stealth_filter.png"
            ],
            minor_upgrade: null,
            major_upgrade: null,
            special: null,
            mechanic: null,
            mechanics: null
        };
        private static const MARKER_ICON_EMBEDDED:Object = {
            minor_upgrade: T11MinorUpgradeAsset,
            major_upgrade: T11MajorUpgradeAsset,
            special: T11CogAsset,
            mechanic: T11StarAsset,
            mechanics: T11StarAsset
        };
        private var combatPercentLabel:TextField;
        private var combatPercentCaption:TextField;
        private var totalPercentLabel:TextField;
        private var totalPercentCaption:TextField;
        private var sideCounterLabel:TextField;
        private var sideCounterCaption:TextField;
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
        private var _barX:Number = SIDE_MARGIN;
        private var _barY:Number = TOP_MARGIN;
        private var _barWidth:Number = MIN_BAR_WIDTH;
        private var _isReady:Boolean = false;
        private var _markerIconBitmapByType:Object = {};
        private var _markerIconLoadStateByType:Object = {};
        private var _markerTooltipDataByDisplay:Dictionary = new Dictionary(true);
        private var _modeIdByButton:Dictionary = new Dictionary(true);
        private var _activeCounterLayout:String = "";
        private var _activeBarFillMode:String = "";
        private var _lastStageWidth:Number = -1;
        private var _lastStageHeight:Number = -1;

        public function ResearchProgressBarLobby() {
            super();
        }

        override protected function configUI():void {
            super.configUI();
            mouseEnabled = false;
            mouseChildren = true;
            build();
            removeEventListener(Event.ENTER_FRAME, onEnterFrame);
            addEventListener(Event.ENTER_FRAME, onEnterFrame, false, 0, true);
            attachStageListeners();
        }

        override protected function onDispose():void {
            hideMarkerTooltip();
            clearModeButtons();
            removeEventListener(Event.ENTER_FRAME, onEnterFrame);
            detachStageListeners();
            super.onDispose();
        }

        override protected function nextFrameAfterPopulateHandler():void {
            super.nextFrameAfterPopulateHandler();
            _isReady = true;
            attachStageListeners();
            layoutFromStage();
            updateTrackedStageSize();
            updateBarFromContext(false);
        }

        private function onEnterFrame(event:Event):void {
            if (!_isReady || stage == null) {
                return;
            }

            if (!updateTrackedStageSize()) {
                return;
            }

            layoutFromStage();
            updateBarFromContext(false);
        }

        private function updateTrackedStageSize():Boolean {
            if (stage == null) {
                return false;
            }

            if (_lastStageWidth == stage.stageWidth && _lastStageHeight == stage.stageHeight) {
                return false;
            }

            _lastStageWidth = stage.stageWidth;
            _lastStageHeight = stage.stageHeight;
            return true;
        }

        private function attachStageListeners():void {
            if (stage == null) {
                return;
            }

            stage.removeEventListener(Event.RESIZE, onStageResize);
            stage.removeEventListener(MouseEvent.MOUSE_MOVE, onStageMouseMove);
            stage.removeEventListener(Event.MOUSE_LEAVE, onStageMouseLeave);
            stage.addEventListener(Event.RESIZE, onStageResize);
            stage.addEventListener(MouseEvent.MOUSE_MOVE, onStageMouseMove, false, 0, true);
            stage.addEventListener(Event.MOUSE_LEAVE, onStageMouseLeave, false, 0, true);
        }

        private function detachStageListeners():void {
            if (stage == null) {
                return;
            }

            stage.removeEventListener(Event.RESIZE, onStageResize);
            stage.removeEventListener(MouseEvent.MOUSE_MOVE, onStageMouseMove);
            stage.removeEventListener(Event.MOUSE_LEAVE, onStageMouseLeave);
        }

        private function build():void {
            combatPercentLabel = makeCounterField();
            addChild(combatPercentLabel);

            combatPercentCaption = makeCounterCaptionField("Vehicle XP");
            addChild(combatPercentCaption);

            totalPercentLabel = makeCounterField();
            addChild(totalPercentLabel);

            totalPercentCaption = makeCounterCaptionField("Total XP");
            addChild(totalPercentCaption);

            sideCounterLabel = makeCounterField();
            alignTextField(sideCounterLabel, TextFormatAlign.LEFT);
            addChild(sideCounterLabel);

            sideCounterCaption = makeCounterCaptionField("");
            alignTextField(sideCounterCaption, TextFormatAlign.LEFT);
            addChild(sideCounterCaption);

            baseBar = createBitmap(ProgressBarBaseAsset);
            addChild(baseBar);

            completedBar = createBitmap(ProgressBarWhiteAsset);
            addChild(completedBar);

            combatBar = createBitmap(ProgressBarGreenAsset);
            addChild(combatBar);

            freeBar = createBitmap(ProgressBarYellowAsset);
            addChild(freeBar);

            completedMaskShape = new Shape();
            completedMaskShape.visible = false;
            addChild(completedMaskShape);

            combatMaskShape = new Shape();
            combatMaskShape.visible = false;
            addChild(combatMaskShape);

            freeMaskShape = new Shape();
            freeMaskShape.visible = false;
            addChild(freeMaskShape);

            completedBar.mask = completedMaskShape;
            combatBar.mask = combatMaskShape;
            freeBar.mask = freeMaskShape;

            markersContainer = new Sprite();
            markersContainer.mouseEnabled = false;
            addChild(markersContainer);

            modeButtonsContainer = new Sprite();
            modeButtonsContainer.mouseEnabled = false;
            modeButtonsContainer.mouseChildren = true;
            modeButtonsContainer.visible = false;
            addChild(modeButtonsContainer);

            tooltipContainer = new Sprite();
            tooltipContainer.mouseEnabled = false;
            tooltipContainer.mouseChildren = false;
            tooltipContainer.visible = false;

            tooltipBackground = new Shape();
            tooltipContainer.addChild(tooltipBackground);

            tooltipContent = new Sprite();
            tooltipContent.mouseEnabled = false;
            tooltipContent.mouseChildren = false;
            tooltipContainer.addChild(tooltipContent);

            addChild(tooltipContainer);
        }

        private function onStageResize(event:Event):void {
            layoutFromStage();
            updateTrackedStageSize();
            updateBarFromContext(false);
        }

        private function onStageMouseMove(event:MouseEvent):void {
            updateTooltipAtStagePoint(event.stageX, event.stageY);
        }

        private function onStageMouseLeave(event:Event):void {
            hideMarkerTooltip();
        }

        public function as_setContext(data:Object):void {
            applyContext(data);
        }

        public function as_setProgress(value:Number):void {
            if (_context == null) {
                _context = {};
            }
            _context.progress = Number(value);
            if (_isReady) {
                updateBarFromContext(false);
            }
        }

        public function as_ping():String {
            return "research-progress-bar-lobby-ready";
        }

        public function as_setVisible(value:Boolean):void {
            visible = value;
            if (!value) {
                hideMarkerTooltip();
            }
        }

        public function as_refreshLayout():void {
            if (!_isReady) {
                return;
            }

            attachStageListeners();
            layoutFromStage();
            updateTrackedStageSize();
            updateBarFromContext(false);
        }

        private function applyContext(data:Object):void {
            if (data == null) {
                return;
            }

            _context = data;

            if (!_isReady) {
                return;
            }

            updateBarFromContext(false);
        }

        private function updateBarFromContext(relayout:Boolean = true):void {
            var modes:Array;
            var activeMode:Object;
            var barMaxValue:Number;
            var completedValue:Number;
            var primaryValue:Number;
            var secondaryValue:Number;
            var completedWidth:Number;
            var primaryWidth:Number;
            var secondaryWidth:Number;
            var totalProgressValue:Number;
            var markerPrimaryValue:Number;
            var markerSecondaryValue:Number;
            var defaultPrimaryPercent:int;
            var defaultTotalPercent:int;

            if (!_isReady || _context == null) {
                return;
            }

            if (baseBar == null || completedBar == null || combatBar == null || freeBar == null || markersContainer == null || modeButtonsContainer == null) {
                return;
            }

            if (relayout) {
                layoutFromStage();
            }

            modes = resolveModes();
            syncSelectedMode(modes);
            rebuildModeButtons(modes);

            activeMode = resolveSelectedMode(modes);
            if (activeMode == null) {
                clearBarPresentation();
                return;
            }

            barMaxValue = Math.max(1, numberValue(activeMode.barMaxValue, numberValue(_context.maxRequirementXp, 1)));
            completedValue = clamp(numberValue(activeMode.completedValue, 0), 0, barMaxValue);
            primaryValue = clamp(numberValue(activeMode.primaryValue, numberValue(_context.combatXp, 0)), 0, barMaxValue - completedValue);
            secondaryValue = clamp(numberValue(activeMode.secondaryValue, numberValue(_context.freeXp, 0)), 0, barMaxValue - completedValue - primaryValue);
            totalProgressValue = clamp(completedValue + primaryValue + secondaryValue, 0, barMaxValue);
            completedWidth = Math.round(_barWidth * completedValue / barMaxValue);
            primaryWidth = Math.round(_barWidth * primaryValue / barMaxValue);
            secondaryWidth = Math.round(_barWidth * secondaryValue / barMaxValue);

            defaultPrimaryPercent = int(Math.min(100, primaryValue * 100 / barMaxValue));
            defaultTotalPercent = int(Math.min(100, (primaryValue + secondaryValue) * 100 / barMaxValue));
            updateCounterFields(activeMode, defaultPrimaryPercent, defaultTotalPercent);

            baseBar.visible = true;
            completedBar.visible = true;
            combatBar.visible = true;
            freeBar.visible = true;
            markersContainer.visible = true;

            if (_activeBarFillMode == BAR_FILL_MODE_COMPLETED_ONLY) {
                completedWidth = Math.round(_barWidth * totalProgressValue / barMaxValue);
                primaryWidth = 0;
                secondaryWidth = 0;
                combatBar.visible = false;
                freeBar.visible = false;
            }

            baseBar.x = _barX;
            baseBar.y = _barY;
            baseBar.width = _barWidth;
            baseBar.height = BAR_HEIGHT;

            completedBar.x = _barX;
            completedBar.y = _barY;
            completedBar.width = _barWidth;
            completedBar.height = BAR_HEIGHT;

            combatBar.x = _barX;
            combatBar.y = _barY;
            combatBar.width = _barWidth;
            combatBar.height = BAR_HEIGHT;

            freeBar.x = _barX;
            freeBar.y = _barY;
            freeBar.width = _barWidth;
            freeBar.height = BAR_HEIGHT;

            drawMask(completedMaskShape, _barX, _barY, completedWidth, BAR_HEIGHT);
            drawMask(combatMaskShape, _barX + completedWidth, _barY, primaryWidth, BAR_HEIGHT);
            drawMask(freeMaskShape, _barX + completedWidth + primaryWidth, _barY, secondaryWidth, BAR_HEIGHT);

            markerPrimaryValue = primaryValue;
            markerSecondaryValue = secondaryValue;
            if (_activeBarFillMode == BAR_FILL_MODE_COMPLETED_ONLY) {
                markerPrimaryValue = totalProgressValue;
                markerSecondaryValue = 0;
            }

            rebuildMarkers(activeMode, barMaxValue, markerPrimaryValue, markerSecondaryValue);
            positionLabels();
        }

        private function clearBarPresentation():void {
            clearMarkers();
            drawMask(completedMaskShape, _barX, _barY, 0, BAR_HEIGHT);
            drawMask(combatMaskShape, _barX, _barY, 0, BAR_HEIGHT);
            drawMask(freeMaskShape, _barX, _barY, 0, BAR_HEIGHT);
            baseBar.visible = false;
            completedBar.visible = false;
            combatBar.visible = false;
            freeBar.visible = false;
            markersContainer.visible = false;
            combatPercentLabel.text = "";
            combatPercentCaption.text = "";
            totalPercentLabel.text = "";
            totalPercentCaption.text = "";
            sideCounterLabel.text = "";
            sideCounterCaption.text = "";
            _activeCounterLayout = "";
            _activeBarFillMode = "";
        }

        private function updateCounterFields(activeMode:Object, defaultPrimaryPercent:int, defaultTotalPercent:int):void {
            var leftCounterText:String;
            var leftCounterCaption:String;
            var rightCounterText:String;
            var rightCounterCaption:String;
            var sideCounterText:String;
            var sideCounterCaption:String;

            _activeCounterLayout = activeMode != null && activeMode.counterLayout !== undefined
                ? String(activeMode.counterLayout)
                : "";
            _activeBarFillMode = activeMode != null && activeMode.barFillMode !== undefined
                ? String(activeMode.barFillMode)
                : "";

            leftCounterText = activeMode != null && activeMode.leftCounterText !== undefined
                ? String(activeMode.leftCounterText)
                : defaultPrimaryPercent.toString() + "%";
            leftCounterCaption = activeMode != null && activeMode.leftCounterCaption !== undefined
                ? String(activeMode.leftCounterCaption)
                : "Vehicle XP";
            rightCounterText = activeMode != null && activeMode.rightCounterText !== undefined
                ? String(activeMode.rightCounterText)
                : defaultTotalPercent.toString() + "%";
            rightCounterCaption = activeMode != null && activeMode.rightCounterCaption !== undefined
                ? String(activeMode.rightCounterCaption)
                : "Total XP";
            sideCounterText = activeMode != null && activeMode.sideCounterText !== undefined
                ? String(activeMode.sideCounterText)
                : "";
            sideCounterCaption = activeMode != null && activeMode.sideCounterCaption !== undefined
                ? String(activeMode.sideCounterCaption)
                : "";

            combatPercentLabel.text = leftCounterText;
            totalPercentLabel.text = rightCounterText;
            totalPercentCaption.text = rightCounterCaption;
            this.sideCounterLabel.text = sideCounterText;
            this.sideCounterCaption.text = sideCounterCaption;

            alignTextField(totalPercentLabel, TextFormatAlign.RIGHT);
            alignTextField(totalPercentCaption, TextFormatAlign.RIGHT);
            alignTextField(this.sideCounterLabel, TextFormatAlign.LEFT);
            alignTextField(this.sideCounterCaption, TextFormatAlign.LEFT);
            totalPercentLabel.width = COUNTER_VALUE_WIDTH;
            totalPercentCaption.width = COUNTER_CAPTION_WIDTH;
            this.sideCounterLabel.width = COUNTER_VALUE_WIDTH;
            this.sideCounterCaption.width = COUNTER_CAPTION_WIDTH;

            if (_activeCounterLayout == COUNTER_LAYOUT_ELITE_STATUS) {
                alignTextField(combatPercentLabel, TextFormatAlign.LEFT);
                alignTextField(combatPercentCaption, TextFormatAlign.LEFT);
                combatPercentLabel.width = ELITE_STATUS_WIDTH;
                combatPercentCaption.width = ELITE_STATUS_WIDTH;
                combatPercentCaption.htmlText = buildEliteStatusCounterHtml(leftCounterCaption);
            }
            else {
                combatPercentCaption.text = leftCounterCaption;
                alignTextField(combatPercentLabel, TextFormatAlign.RIGHT);
                alignTextField(combatPercentCaption, TextFormatAlign.RIGHT);
                combatPercentLabel.width = COUNTER_VALUE_WIDTH;
                combatPercentCaption.width = COUNTER_CAPTION_WIDTH;
            }
        }

        private function resolveModes():Array {
            if (_context == null) {
                return [];
            }

            if (_context.modes is Array) {
                return _context.modes as Array;
            }

            return [ {
                    id: "legacy_research",
                    buttonLabel: "Research",
                    barMaxValue: _context.maxRequirementXp,
                    completedValue: _context.completedValue,
                    primaryValue: _context.combatXp,
                    secondaryValue: _context.freeXp,
                    leftCounterText: _context.leftCounterText,
                    leftCounterCaption: _context.leftCounterCaption,
                    rightCounterText: _context.rightCounterText,
                    rightCounterCaption: _context.rightCounterCaption,
                    sideCounterText: _context.sideCounterText,
                    sideCounterCaption: _context.sideCounterCaption,
                    markers: _context.markers
                }
            ];
        }

        private function syncSelectedMode(modes:Array):void {
            var requestedModeId:String = _context != null && _context.selectedModeId !== undefined
                ? String(_context.selectedModeId)
                : null;

            if (!hasModeId(modes, _selectedModeId)) {
                _selectedModeId = null;
            }

            if (_selectedModeId == null && hasModeId(modes, requestedModeId)) {
                _selectedModeId = requestedModeId;
            }

            if (_selectedModeId == null && modes != null && modes.length > 0) {
                _selectedModeId = modeIdOf(modes[0]);
            }
        }

        private function hasModeId(modes:Array, modeId:String):Boolean {
            var mode:Object;

            if (modeId == null || modes == null) {
                return false;
            }

            for each (mode in modes) {
                if (modeIdOf(mode) == modeId) {
                    return true;
                }
            }

            return false;
        }

        private function resolveSelectedMode(modes:Array):Object {
            var mode:Object;

            if (modes == null) {
                return null;
            }

            for each (mode in modes) {
                if (modeIdOf(mode) == _selectedModeId) {
                    return mode;
                }
            }

            return null;
        }

        private function modeIdOf(mode:Object):String {
            if (mode == null || mode.id === undefined || mode.id == null) {
                return null;
            }

            return String(mode.id);
        }

        private function rebuildModeButtons(modes:Array):void {
            var totalWidth:Number = measureModeButtonsWidth(modes);
            var cursorX:Number = Math.max(BAR_MIN_STAGE_SIDE_MARGIN, _barX - MODE_BUTTON_BAR_GAP - totalWidth);
            var buttonHeight:Number = MODE_BUTTON_HEIGHT + MODE_BUTTON_BOTTOM_PADDING;
            var buttonY:Number = _barY + Math.round((BAR_HEIGHT - buttonHeight) * 0.5);
            var mode:Object;
            var button:Sprite;

            clearModeButtons();

            if (modeButtonsContainer == null || modes == null || modes.length == 0) {
                return;
            }

            modeButtonsContainer.visible = true;

            for each (mode in modes) {
                button = createModeButton(resolveModeButtonLabel(mode), modeIdOf(mode) == _selectedModeId);
                button.x = cursorX;
                button.y = buttonY;
                button.buttonMode = true;
                button.useHandCursor = true;
                button.mouseEnabled = true;
                button.addEventListener(MouseEvent.CLICK, onModeButtonClick, false, 0, true);
                _modeIdByButton[button] = modeIdOf(mode);
                modeButtonsContainer.addChild(button);
                cursorX += button.width + MODE_BUTTON_GAP;
            }
        }

        private function clearModeButtons():void {
            var child:Sprite;

            if (modeButtonsContainer == null) {
                return;
            }

            while (modeButtonsContainer.numChildren > 0) {
                child = modeButtonsContainer.removeChildAt(0) as Sprite;
                if (child != null) {
                    child.removeEventListener(MouseEvent.CLICK, onModeButtonClick);
                }
            }

            _modeIdByButton = new Dictionary(true);
            modeButtonsContainer.visible = false;
        }

        private function onModeButtonClick(event:MouseEvent):void {
            var button:Sprite = event.currentTarget as Sprite;
            var modeId:String;

            if (button == null) {
                return;
            }

            modeId = _modeIdByButton[button];
            if (modeId == null || modeId == _selectedModeId) {
                return;
            }

            _selectedModeId = modeId;
            hideMarkerTooltip();
            updateBarFromContext(false);
        }

        private function resolveModeButtonLabel(mode:Object):String {
            if (mode != null && mode.buttonLabel !== undefined && mode.buttonLabel != null) {
                return String(mode.buttonLabel);
            }

            return "Mode";
        }

        private function measureModeButtonsWidth(modes:Array):Number {
            var totalWidth:Number = 0;
            var mode:Object;

            if (modes == null || modes.length == 0) {
                return 0;
            }

            for each (mode in modes) {
                totalWidth += measureModeButtonWidth(resolveModeButtonLabel(mode));
            }

            if (modes.length > 1) {
                totalWidth += MODE_BUTTON_GAP * (modes.length - 1);
            }

            return totalWidth;
        }

        private function measureModeButtonWidth(label:String):Number {
            var field:TextField = makeTextField(MODE_BUTTON_TEXT_COLOR, 12, true);

            field.text = label;
            return Math.max(MODE_BUTTON_MIN_WIDTH, field.textWidth + MODE_BUTTON_PADDING_X * 2 + 6);
        }

        private function createModeButton(label:String, isSelected:Boolean):Sprite {
            var button:Sprite = new Sprite();
            var background:Shape = new Shape();
            var field:TextField = makeTextField(
                isSelected ? MODE_BUTTON_TEXT_ACTIVE_COLOR : MODE_BUTTON_TEXT_COLOR,
                12,
                true
            );
            var buttonWidth:Number;

            field.text = label;
            buttonWidth = Math.max(MODE_BUTTON_MIN_WIDTH, field.textWidth + MODE_BUTTON_PADDING_X * 2 + 6);
            drawModeButtonBackground(background, buttonWidth, MODE_BUTTON_HEIGHT + MODE_BUTTON_BOTTOM_PADDING, isSelected);
            button.addChild(background);

            field.width = buttonWidth;
            field.height = MODE_BUTTON_HEIGHT + 4;
            alignTextField(field, TextFormatAlign.CENTER);
            field.y = resolveCenteredTextY(field, 0, MODE_BUTTON_HEIGHT) + 1;
            button.addChild(field);

            return button;
        }

        private function drawModeButtonBackground(shape:Shape, width:Number, height:Number, isSelected:Boolean):void {
            shape.graphics.clear();
            shape.graphics.lineStyle(
                1,
                isSelected ? MODE_BUTTON_BORDER_ACTIVE_COLOR : MODE_BUTTON_BORDER_COLOR,
                1.0
            );
            shape.graphics.beginFill(
                isSelected ? MODE_BUTTON_BACKGROUND_ACTIVE_COLOR : MODE_BUTTON_BACKGROUND_COLOR,
                0.95
            );
            shape.graphics.drawRoundRect(0, 0, width, height, 6, 6);
            shape.graphics.endFill();
        }

        private function rebuildMarkers(activeMode:Object, maxRequirementXp:Number, combatXp:Number, freeXp:Number):void {
            var marker:Object;
            var markerPositionValue:Number;
            var markerX:Number;
            var markerDisplay:Sprite;

            clearMarkers();

            if (activeMode == null || !(activeMode.markers is Array)) {
                return;
            }

            for each (marker in activeMode.markers) {
                markerPositionValue = clamp(
                    numberValue(
                        marker != null && marker.positionValue !== undefined
                            ? marker.positionValue
                            : marker.costXp,
                        0
                    ),
                    0,
                    maxRequirementXp
                );
                markerX = Math.round(_barWidth * markerPositionValue / maxRequirementXp);
                markerDisplay = createMarkerDisplay(marker, markerPositionValue, combatXp, freeXp);
                markerDisplay.x = _barX + markerX;
                markerDisplay.y = _barY;
                updateMarkerHitArea(markerDisplay);
                markersContainer.addChild(markerDisplay);
            }
        }

        private function clearMarkers():void {
            hideMarkerTooltip();
            _markerTooltipDataByDisplay = new Dictionary(true);

            if (markersContainer == null) {
                return;
            }

            while (markersContainer.numChildren > 0) {
                markersContainer.removeChildAt(0);
            }
        }

        private function createMarkerDisplay(marker:Object, markerProgressValue:Number, combatXp:Number, freeXp:Number):Sprite {
            var markerSprite:Sprite = new Sprite();
            var markerTooltipValue:Number = numberValue(
                marker != null && marker.costXp !== undefined ? marker.costXp : markerProgressValue,
                markerProgressValue
            );
            var markerBitmap:Bitmap = createMarkerBitmap(marker, markerProgressValue, combatXp, freeXp);
            var markerIcon:Bitmap;
            var markerLabel:TextField;
            var markerLabelText:String = marker != null && marker.label !== undefined ? String(marker.label) : "";

            markerBitmap.x = -Math.round(markerBitmap.width / 2);
            markerBitmap.y = -Math.round((markerBitmap.height - BAR_HEIGHT) / 2);
            markerSprite.addChild(markerBitmap);

            markerIcon = createMarkerIcon(marker, markerBitmap.y);
            if (markerIcon != null) {
                markerSprite.addChild(markerIcon);
            }
            else if (markerLabelText.length > 0) {
                markerLabel = makeMarkerLabelField(markerLabelText, markerBitmap.y);
                markerSprite.addChild(markerLabel);
            }

            markerSprite.mouseEnabled = true;
            markerSprite.mouseChildren = false;
            markerSprite.addEventListener(MouseEvent.MOUSE_OVER, onMarkerMouseOver, false, 0, true);
            markerSprite.addEventListener(MouseEvent.MOUSE_OUT, onMarkerMouseOut, false, 0, true);
            _markerTooltipDataByDisplay[markerSprite] = {
                marker: marker,
                costXp: markerTooltipValue,
                combatXp: combatXp,
                freeXp: freeXp
            };

            return markerSprite;
        }

        private function updateMarkerHitArea(markerDisplay:Sprite):void {
            var bounds:Rectangle;

            if (markerDisplay == null) {
                return;
            }

            bounds = markerDisplay.getBounds(markerDisplay);
            if (bounds == null) {
                return;
            }

            markerDisplay.graphics.clear();
            markerDisplay.graphics.beginFill(0x000000, 0.0);
            markerDisplay.graphics.drawRect(bounds.x, bounds.y - 2, bounds.width, bounds.height + 4);
            markerDisplay.graphics.endFill();
        }

        private function createMarkerBitmap(marker:Object, markerProgressValue:Number, combatXp:Number, freeXp:Number):Bitmap {
            var markerState:String = marker != null && marker.markerState !== undefined ? String(marker.markerState) : "";

            if (markerState == "completed") {
                return createBitmap(MarkerWhiteAsset);
            }
            if (markerState == "reachable_vehicle") {
                return createBitmap(MarkerGreenAsset);
            }
            if (markerState == "reachable_total") {
                return createBitmap(MarkerYellowAsset);
            }
            if (markerState == "locked") {
                return createBitmap(MarkerDefaultAsset);
            }
            if (marker != null && marker.isAvailable !== undefined && !Boolean(marker.isAvailable)) {
                return createBitmap(MarkerDefaultAsset);
            }
            if (markerProgressValue <= combatXp) {
                return createBitmap(MarkerGreenAsset);
            }
            if (markerProgressValue <= combatXp + freeXp) {
                return createBitmap(MarkerYellowAsset);
            }
            return createBitmap(MarkerDefaultAsset);
        }

        private function shouldHideTooltipIcon(marker:Object):Boolean {
            return marker != null && marker.hideTooltipIcon !== undefined && Boolean(marker.hideTooltipIcon);
        }

        private function shouldHideBarIcon(marker:Object):Boolean {
            return marker != null && marker.hideBarIcon !== undefined && Boolean(marker.hideBarIcon);
        }

        private function onMarkerMouseOver(event:MouseEvent):void {
            updateTooltipAtStagePoint(event.stageX, event.stageY);
        }

        private function onMarkerMouseOut(event:MouseEvent):void {
            updateTooltipAtStagePoint(event.stageX, event.stageY);
        }

        private function updateTooltipAtStagePoint(stageX:Number, stageY:Number):void {
            var tooltipEntries:Array = [];
            var candidate:Sprite;
            var candidateBounds:Rectangle;
            var candidateData:Object;
            var idx:int;

            if (!visible || markersContainer == null) {
                hideMarkerTooltip();
                return;
            }

            for (idx = 0; idx < markersContainer.numChildren; idx++) {
                candidate = markersContainer.getChildAt(idx) as Sprite;
                if (candidate == null) {
                    continue;
                }

                candidateBounds = candidate.getBounds(stage);
                if (candidateBounds == null || !candidateBounds.contains(stageX, stageY)) {
                    continue;
                }

                candidateData = _markerTooltipDataByDisplay[candidate];
                if (candidateData != null) {
                    tooltipEntries.push(candidateData);
                }
            }

            if (tooltipEntries.length == 0) {
                hideMarkerTooltip();
                return;
            }

            showTooltipEntries(tooltipEntries, stageX, stageY);
        }

        private function showTooltipEntries(entries:Array, stageX:Number, stageY:Number):void {
            var entry:Object;
            var section:Sprite;
            var sectionBounds:Rectangle;
            var contentBounds:Rectangle;
            var cursorY:Number = 0;
            var idx:int;
            var tooltipWidth:Number;
            var tooltipHeight:Number;

            if (tooltipContainer == null || tooltipContent == null || tooltipBackground == null) {
                return;
            }

            clearTooltipContent();

            for (idx = 0; idx < entries.length; idx++) {
                entry = entries[idx];
                section = buildTooltipSection(entry);
                section.y = cursorY;
                tooltipContent.addChild(section);
                sectionBounds = section.getBounds(section);
                cursorY += sectionBounds.height;
                if (idx < entries.length - 1) {
                    cursorY += TOOLTIP_SECTION_GAP;
                }
            }

            contentBounds = tooltipContent.getBounds(tooltipContent);
            tooltipContent.x = TOOLTIP_PADDING_X - contentBounds.x;
            tooltipContent.y = TOOLTIP_PADDING_Y - contentBounds.y;

            tooltipWidth = contentBounds.width + TOOLTIP_PADDING_X * 2;
            tooltipHeight = contentBounds.height + TOOLTIP_PADDING_Y + TOOLTIP_PADDING_BOTTOM;
            drawTooltipBackground(tooltipWidth, tooltipHeight);

            tooltipContainer.visible = true;
            positionTooltip(stageX, stageY, tooltipWidth, tooltipHeight);
        }

        private function clearTooltipContent():void {
            if (tooltipContent == null) {
                return;
            }

            while (tooltipContent.numChildren > 0) {
                tooltipContent.removeChildAt(0);
            }
        }

        private function hideMarkerTooltip():void {
            if (tooltipContainer != null) {
                tooltipContainer.visible = false;
            }
        }

        private function positionTooltip(stageX:Number, stageY:Number, tooltipWidth:Number, tooltipHeight:Number):void {
            var tooltipX:Number = stageX - Math.round(tooltipWidth / 2);
            var tooltipY:Number = stageY + TOOLTIP_OFFSET_Y;
            var minX:Number = 4;
            var maxX:Number;
            var minY:Number = 4;
            var maxY:Number;

            if (stage != null) {
                maxX = stage.stageWidth - tooltipWidth - 4;
                maxY = stage.stageHeight - tooltipHeight - 4;
                if (tooltipX < minX) {
                    tooltipX = minX;
                }
                if (tooltipX > maxX) {
                    tooltipX = maxX;
                }

                if (tooltipY > maxY) {
                    tooltipY = stageY - tooltipHeight - TOOLTIP_OFFSET_Y;
                }

                if (tooltipY < minY) {
                    tooltipY = minY;
                }
                if (tooltipY > maxY) {
                    tooltipY = maxY;
                }
            }

            tooltipContainer.x = Math.round(tooltipX);
            tooltipContainer.y = Math.round(tooltipY);
        }

        private function drawTooltipBackground(width:Number, height:Number):void {
            tooltipBackground.graphics.clear();
            tooltipBackground.graphics.lineStyle(1, TOOLTIP_BORDER_COLOR, 1.0);
            tooltipBackground.graphics.beginFill(TOOLTIP_BACKGROUND_COLOR, TOOLTIP_BACKGROUND_ALPHA);
            tooltipBackground.graphics.drawRoundRect(0, 0, width, height, 6, 6);
            tooltipBackground.graphics.endFill();
        }

        private function buildTooltipSection(entry:Object):Sprite {
            var section:Sprite = new Sprite();
            var marker:Object = entry.marker;
            var markerCostXp:Number = Number(entry.costXp);
            var combatXp:Number = Number(entry.combatXp);
            var freeXp:Number = Number(entry.freeXp);
            var row:Sprite;
            var rowBounds:Rectangle;
            var cursorY:Number = 0;
            var markerState:String = marker != null && marker.markerState !== undefined ? String(marker.markerState) : "";
            var prereq:Object;
            var prereqs:Array;
            var progressLabel:String = marker != null && marker.progressLabel !== undefined ? String(marker.progressLabel) : "Vehicle XP";
            var singleProgressRow:Boolean = marker != null && marker.singleProgressRow !== undefined && Boolean(marker.singleProgressRow);

            row = createTooltipTitleCostRow(marker, markerCostXp);
            row.y = cursorY;
            section.addChild(row);
            rowBounds = row.getBounds(row);
            cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

            var debugText:String = resolveMarkerDebugText(marker);
            if (debugText.length > 0) {
                row = createTooltipTextRow(
                    debugText,
                    TOOLTIP_BODY_SIZE,
                    TOOLTIP_MUTED_TEXT_COLOR,
                    false
                );
                row.y = cursorY;
                section.addChild(row);
                rowBounds = row.getBounds(row);
                cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
            }

            if (markerState == "completed") {
                row = createTooltipTextRow(
                    "Unlocked",
                    TOOLTIP_BODY_SIZE,
                    TOOLTIP_HIGHLIGHT_TEXT_COLOR,
                    true
                );
                row.y = cursorY;
                section.addChild(row);
                return section;
            }

            if (marker != null && marker.isAvailable !== undefined && !Boolean(marker.isAvailable)) {
                row = createTooltipTextRow(
                    "Prerequisites:",
                    TOOLTIP_BODY_SIZE,
                    TOOLTIP_MUTED_TEXT_COLOR,
                    false
                );
                row.y = cursorY;
                section.addChild(row);
                rowBounds = row.getBounds(row);
                cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

                prereqs = marker != null && marker.missingPrereqs is Array ? marker.missingPrereqs as Array : [];
                for each (prereq in prereqs) {
                    row = createTooltipIconTextRow(
                        prereq != null && prereq.item_type !== undefined ? String(prereq.item_type) : "unknown",
                        prereq != null && prereq.label !== undefined ? String(prereq.label) : "?",
                        resolveTooltipItemLabel(prereq),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_TEXT_COLOR,
                        false,
                        TOOLTIP_COMPACT_ICON_SIZE
                    );
                    row.y = cursorY;
                    section.addChild(row);
                    rowBounds = row.getBounds(row);
                    cursorY += rowBounds.height + TOOLTIP_COMPACT_ROW_GAP;
                }

                if (prereqs.length == 0) {
                    row = createTooltipTextRow(
                        resolveLockedBehindText(marker),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_TEXT_COLOR,
                        false
                    );
                    row.y = cursorY;
                    section.addChild(row);
                    rowBounds = row.getBounds(row);
                    cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
                }

                return section;
            }

            row = createTooltipProgressRow(progressLabel, combatXp, markerCostXp);
            row.y = cursorY;
            section.addChild(row);
            rowBounds = row.getBounds(row);
            cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

            if (singleProgressRow) {
                return section;
            }

            row = createTooltipProgressRow("Total XP", combatXp + freeXp, markerCostXp);
            row.y = cursorY;
            section.addChild(row);

            return section;
        }

        private function resolveLockedBehindText(marker:Object):String {
            var prereqNames:Array;
            var prereqText:String;

            if (marker != null && marker.missingPrereqNames is Array) {
                prereqNames = marker.missingPrereqNames as Array;
                if (prereqNames.length == 1) {
                    return String(prereqNames[0]);
                }
                if (prereqNames.length > 1) {
                    prereqText = prereqNames.join(", ");
                    return prereqText;
                }
            }

            return "missing prerequisites";
        }

        private function createTooltipProgressRow(label:String, currentXp:Number, targetXp:Number):Sprite {
            var row:Sprite = new Sprite();
            var labelField:TextField;
            var percentField:TextField;
            var statusField:TextField;
            var pct:int;
            var missingXp:Number;
            var statusText:String;
            var rowHeight:Number;

            if (targetXp <= 0) {
                pct = 100;
                missingXp = 0;
            }
            else {
                pct = int(Math.min(100, currentXp * 100 / targetXp));
                missingXp = Math.max(0, targetXp - currentXp);
            }

            if (missingXp <= 0) {
                statusText = "ready for research";
                statusField = makeTooltipRowField(statusText, TOOLTIP_BODY_SIZE, TOOLTIP_TEXT_COLOR, false);
            }
            else {
                statusField = makeTooltipHtmlRowField(
                    buildTooltipHighlightedHtml("", formatExactXpValue(missingXp), " XP left", true),
                    TOOLTIP_BODY_SIZE,
                    TOOLTIP_TEXT_COLOR,
                    false
                );
            }

            labelField = makeTooltipRowField(label, TOOLTIP_BODY_SIZE, TOOLTIP_MUTED_TEXT_COLOR, false);
            labelField.width = TOOLTIP_PROGRESS_LABEL_WIDTH;
            alignTextField(labelField, TextFormatAlign.RIGHT);
            row.addChild(labelField);

            percentField = makeTooltipRowField(pct.toString() + "%", TOOLTIP_BODY_SIZE, TOOLTIP_HIGHLIGHT_TEXT_COLOR, true);
            percentField.width = TOOLTIP_PROGRESS_PERCENT_WIDTH;
            percentField.x = TOOLTIP_PROGRESS_LABEL_WIDTH + TOOLTIP_PROGRESS_GAP;
            alignTextField(percentField, TextFormatAlign.RIGHT);
            row.addChild(percentField);

            statusField.x = percentField.x + TOOLTIP_PROGRESS_PERCENT_WIDTH + TOOLTIP_PROGRESS_GAP;
            row.addChild(statusField);

            rowHeight = Math.max(labelField.height, Math.max(percentField.height, statusField.height));
            labelField.y = Math.round((rowHeight - labelField.height) / 2);
            percentField.y = Math.round((rowHeight - percentField.height) / 2);
            statusField.y = Math.round((rowHeight - statusField.height) / 2);
            return row;
        }

        private function createTooltipTitleCostRow(marker:Object, costXp:Number):Sprite {
            var row:Sprite = new Sprite();
            var icon:Sprite = null;
            var tooltipIconSize:Number = resolveMarkerTooltipIconSize(marker);
            var tooltipIconLayoutWidth:Number = Math.max(TOOLTIP_ICON_LAYOUT_WIDTH, tooltipIconSize);
            var titleField:TextField = makeTooltipRowField(resolveMarkerTooltipTitle(marker), TOOLTIP_TITLE_SIZE, TOOLTIP_TEXT_COLOR, true);
            var costField:TextField = makeTooltipHtmlRowField(
                buildTooltipHighlightedHtml("", formatExactXpValue(costXp), " XP", true),
                TOOLTIP_BODY_SIZE,
                TOOLTIP_MUTED_TEXT_COLOR,
                false
            );
            var rowHeight:Number;
            var textBlockHeight:Number;
            var textBlockTop:Number;
            var titleX:Number = 0;

            if (!shouldHideTooltipIcon(marker)) {
                icon = createTooltipMarkerIconForMarker(marker, marker != null && marker.label !== undefined ? String(marker.label) : "?", tooltipIconSize, tooltipIconLayoutWidth);
            }
            else {
                icon = createTransparentTooltipIconPlaceholder(tooltipIconSize, tooltipIconLayoutWidth);
            }

            if (icon != null) {
                row.addChild(icon);
                titleX = tooltipIconLayoutWidth + TOOLTIP_ICON_GAP;
            }

            if (isT11Marker(marker)) {
                titleX += 5;
            }

            if (isEliteMarker(marker)) {
                titleX += 10;
            }

            titleField.x = titleX;
            row.addChild(titleField);

            costField.x = titleField.x + titleField.width + TOOLTIP_PROGRESS_GAP;
            row.addChild(costField);

            rowHeight = Math.max(tooltipIconSize, Math.max(titleField.height, costField.height));
            if (icon != null) {
                icon.y = Math.round((rowHeight - tooltipIconSize) / 2);
            }
            textBlockHeight = Math.max(titleField.height, costField.height);
            textBlockTop = Math.round((rowHeight - textBlockHeight) / 2);
            titleField.y = textBlockTop + (textBlockHeight - titleField.height);
            costField.y = textBlockTop + (textBlockHeight - costField.height);

            return row;
        }

        private function isT11Marker(marker:Object):Boolean {
            var markerId:String;

            if (marker == null || marker.id === undefined || marker.id == null) {
                return false;
            }

            markerId = String(marker.id);
            return markerId.indexOf("t11_") == 0;
        }

        private function isEliteMarker(marker:Object):Boolean {
            var markerId:String;

            if (marker == null || marker.id === undefined || marker.id == null) {
                return false;
            }

            markerId = String(marker.id);
            return markerId.indexOf("elite_") == 0;
        }

        private function resolveMarkerTooltipTitle(marker:Object):String {
            var markerName:String = resolveMarkerName(marker);
            var levelValue:*;

            if (!isEliteMarker(marker) || marker == null || marker.level === undefined || marker.level == null) {
                return markerName;
            }

            levelValue = marker.level;
            return "Level " + String(levelValue) + ": " + markerName;
        }

        private function resolveMarkerTooltipIconSize(marker:Object):Number {
            if (marker != null && marker.tooltipIconSize !== undefined && marker.tooltipIconSize != null) {
                return Number(marker.tooltipIconSize);
            }

            return TOOLTIP_ICON_SIZE;
        }

        private function createTooltipIconTextRow(itemType:String, fallbackLabel:String, text:String, size:int, color:uint, bold:Boolean, iconSize:Number = TOOLTIP_ICON_SIZE):Sprite {
            var row:Sprite = new Sprite();
            var icon:Sprite = createTooltipMarkerIcon(itemType, fallbackLabel, iconSize);
            var field:TextField = makeTooltipRowField(text, size, color, bold);
            var rowHeight:Number;

            if (icon != null) {
                row.addChild(icon);
            }

            field.x = TOOLTIP_ICON_LAYOUT_WIDTH + TOOLTIP_ICON_GAP;
            row.addChild(field);

            rowHeight = Math.max(iconSize, field.height);
            if (icon != null) {
                icon.y = Math.round((rowHeight - iconSize) / 2);
            }
            field.y = Math.round((rowHeight - field.height) / 2);
            return row;
        }

        private function createTransparentTooltipIconPlaceholder(iconSize:Number = TOOLTIP_ICON_SIZE, layoutWidth:Number = TOOLTIP_ICON_LAYOUT_WIDTH):Sprite {
            var iconSprite:Sprite = new Sprite();

            iconSprite.graphics.beginFill(0xFFFFFF, 0.0);
            iconSprite.graphics.drawRect(0, 0, layoutWidth, iconSize);
            iconSprite.graphics.endFill();
            return iconSprite;
        }

        private function createTooltipTextRow(text:String, size:int, color:uint, bold:Boolean):Sprite {
            var row:Sprite = new Sprite();
            var field:TextField = makeTooltipRowField(text, size, color, bold);
            row.addChild(field);
            return row;
        }

        private function createTooltipMarkerIcon(itemType:String, fallbackLabel:String, iconSize:Number = TOOLTIP_ICON_SIZE, layoutWidth:Number = TOOLTIP_ICON_LAYOUT_WIDTH):Sprite {
            var iconSprite:Sprite = new Sprite();
            var bitmapData:BitmapData = getMarkerIconBitmapData(itemType);
            var iconBitmap:Bitmap;
            var scale:Number;
            var labelField:TextField;

            if (bitmapData != null) {
                iconBitmap = new Bitmap(bitmapData);
                iconBitmap.smoothing = true;
                scale = iconSize / Math.max(iconBitmap.width, iconBitmap.height);
                iconBitmap.scaleX = scale;
                iconBitmap.scaleY = scale;
                iconBitmap.x = Math.round((layoutWidth - iconBitmap.width) / 2);
                iconBitmap.y = Math.round((iconSize - iconBitmap.height) / 2);
                iconSprite.addChild(iconBitmap);
                return iconSprite;
            }

            labelField = makeTooltipRowField(fallbackLabel, TOOLTIP_BODY_SIZE, TOOLTIP_TEXT_COLOR, true);
            labelField.width = layoutWidth;
            labelField.height = iconSize;
            alignTextField(labelField, TextFormatAlign.CENTER);
            labelField.y = Math.round((iconSize - labelField.height) / 2);
            iconSprite.addChild(labelField);
            return iconSprite;
        }

        private function createTooltipMarkerIconForMarker(marker:Object, fallbackLabel:String, iconSize:Number = TOOLTIP_ICON_SIZE, layoutWidth:Number = TOOLTIP_ICON_LAYOUT_WIDTH):Sprite {
            var iconSprite:Sprite = new Sprite();
            var bitmapData:BitmapData = getMarkerIconBitmapDataForMarker(marker);
            var iconBitmap:Bitmap;
            var scale:Number;
            var labelField:TextField;

            if (bitmapData != null) {
                iconBitmap = new Bitmap(bitmapData);
                iconBitmap.smoothing = true;
                scale = iconSize / Math.max(iconBitmap.width, iconBitmap.height);
                iconBitmap.scaleX = scale;
                iconBitmap.scaleY = scale;
                iconBitmap.x = Math.round((layoutWidth - iconBitmap.width) / 2);
                iconBitmap.y = Math.round((iconSize - iconBitmap.height) / 2);
                iconSprite.addChild(iconBitmap);
                return iconSprite;
            }

            labelField = makeTooltipRowField(fallbackLabel, TOOLTIP_BODY_SIZE, TOOLTIP_TEXT_COLOR, true);
            labelField.width = layoutWidth;
            labelField.height = iconSize;
            alignTextField(labelField, TextFormatAlign.CENTER);
            labelField.y = Math.round((iconSize - labelField.height) / 2);
            iconSprite.addChild(labelField);
            return iconSprite;
        }

        private function makeTooltipRowField(text:String, size:int, color:uint, bold:Boolean):TextField {
            var field:TextField = makeTextField(color, size, bold);
            field.text = text;
            field.width = field.textWidth + 6;
            field.height = field.textHeight + 6;
            return field;
        }

        private function makeTooltipHtmlRowField(html:String, size:int, color:uint, bold:Boolean):TextField {
            var field:TextField = makeTextField(color, size, bold);
            field.htmlText = html;
            field.width = field.textWidth + 6;
            field.height = field.textHeight + 6;
            return field;
        }

        private function buildTooltipHighlightedHtml(prefix:String, highlightedText:String, suffix:String, highlightBold:Boolean):String {
            var html:String = escapeHtml(prefix);

            html += "<font color='#" + formatHtmlColor(TOOLTIP_HIGHLIGHT_TEXT_COLOR) + "'>";
            if (highlightBold) {
                html += "<b>";
            }
            html += escapeHtml(highlightedText);
            if (highlightBold) {
                html += "</b>";
            }
            html += "</font>";
            html += escapeHtml(suffix);
            return html;
        }

        private function buildEliteStatusCounterHtml(text:String):String {
            var suffix:String = " Base XP";

            if (text == null) {
                return "";
            }

            if (text.length > suffix.length && text.substr(text.length - suffix.length) == suffix) {
                return buildTooltipHighlightedHtml("", text.substr(0, text.length - suffix.length), suffix, true);
            }

            return escapeHtml(text);
        }

        private function escapeHtml(text:String):String {
            if (text == null) {
                return "";
            }

            return text.split("&").join("&amp;").split("<").join("&lt;").split(">") .join("&gt;");
        }

        private function formatHtmlColor(color:uint):String {
            var hex:String = color.toString(16).toUpperCase();

            while (hex.length < 6) {
                hex = "0" + hex;
            }

            return hex;
        }

        private function resolveTooltipItemLabel(item:Object):String {
            if (item != null && item.name !== undefined && item.name != null && String(item.name).length > 0) {
                return String(item.name);
            }

            if (item != null && item.item_type !== undefined) {
                return resolveMarkerName({itemType: item.item_type});
            }

            return resolveMarkerName(null);
        }

        private function resolveMarkerName(marker:Object):String {
            var explicitName:String;
            var itemType:String;

            if (marker != null && marker.name !== undefined && marker.name != null) {
                explicitName = String(marker.name);
                if (explicitName.length > 0) {
                    return explicitName;
                }
            }

            itemType = marker != null && marker.itemType !== undefined ? String(marker.itemType) : "unknown";
            if (MARKER_TYPE_NAMES.hasOwnProperty(itemType)) {
                return String(MARKER_TYPE_NAMES[itemType]);
            }

            return String(MARKER_TYPE_NAMES.unknown);
        }

        private function resolveMarkerDebugText(marker:Object):String {
            var parts:Array = [];
            var slotCategory:String;

            if (marker != null && marker.debugSlotCategory !== undefined && marker.debugSlotCategory != null) {
                slotCategory = String(marker.debugSlotCategory);
                if (slotCategory.length > 0 && slotCategory != "universal") {
                    parts.push("slot: " + slotCategory);
                }
            }

            return parts.join(" | ");
        }

        private function createMarkerIcon(marker:Object, markerTopY:Number):Bitmap {
            var bitmapData:BitmapData = getMarkerBarIconBitmapDataForMarker(marker);
            var iconSize:Number;
            var icon:Bitmap;
            var scale:Number;
            var yOffset:Number;

            if (shouldHideBarIcon(marker)) {
                return null;
            }

            if (bitmapData == null) {
                return null;
            }

            icon = new Bitmap(bitmapData);
            icon.smoothing = true;
            iconSize = marker != null && marker.barIconSize !== undefined ? Number(marker.barIconSize) : MARKER_ICON_SIZE;
            yOffset = marker != null && marker.barIconYOffset !== undefined ? Number(marker.barIconYOffset) : MARKER_ICON_Y_OFFSET;
            scale = iconSize / Math.max(icon.width, icon.height);
            icon.scaleX = scale;
            icon.scaleY = scale;
            icon.x = -Math.round(icon.width / 2);
            icon.y = markerTopY - icon.height + yOffset;
            return icon;
        }

        private function getMarkerBarIconBitmapDataForMarker(marker:Object):BitmapData {
            var barItemType:String;

            barItemType = resolveMarkerBarItemType(marker);
            if (barItemType.length > 0) {
                return getMarkerIconBitmapData(barItemType);
            }

            return getMarkerIconBitmapDataForMarker(marker);
        }

        private function resolveMarkerBarItemType(marker:Object):String {
            var itemType:String;
            var iconCacheKey:String;
            var cacheParts:Array;

            if (marker == null) {
                return "";
            }

            if (marker.barItemType !== undefined && marker.barItemType != null) {
                return String(marker.barItemType);
            }

            if (marker.debugCategory !== undefined && marker.debugCategory != null) {
                return String(marker.debugCategory);
            }

            if (marker.itemType !== undefined && marker.itemType != null) {
                itemType = String(marker.itemType);
                if (itemType != "unknown") {
                    return itemType;
                }
            }

            if (marker.iconCacheKey !== undefined && marker.iconCacheKey != null) {
                iconCacheKey = String(marker.iconCacheKey);
                if (iconCacheKey.indexOf("t11:") == 0) {
                    cacheParts = iconCacheKey.split(":");
                    if (cacheParts.length >= 3) {
                        return String(cacheParts[1]);
                    }
                }
            }

            return "";
        }

        private function getMarkerIconBitmapDataForMarker(marker:Object):BitmapData {
            return getMarkerIconBitmapDataByKey(resolveMarkerIconKey(marker), resolveMarkerIconPaths(marker));
        }

        private function getEmbeddedMarkerIconBitmapData(itemType:String):BitmapData {
            if (itemType == null || !MARKER_ICON_EMBEDDED.hasOwnProperty(itemType)) {
                return null;
            }
            var assetClass:Class = MARKER_ICON_EMBEDDED[itemType] as Class;
            if (assetClass == null) {
                return null;
            }
            var assetBitmap:Bitmap = new assetClass() as Bitmap;
            if (assetBitmap == null) {
                return null;
            }
            return assetBitmap.bitmapData;
        }

        private function getMarkerIconBitmapData(itemType:String):BitmapData {
            var embedded:BitmapData = getEmbeddedMarkerIconBitmapData(itemType);
            if (embedded != null) {
                return embedded;
            }
            return getMarkerIconBitmapDataByKey(itemType != null ? itemType : "", getMarkerIconPaths(itemType));
        }

        private function getMarkerIconBitmapDataByKey(iconKey:String, paths:Array):BitmapData {
            var normalizedType:String = iconKey != null ? iconKey : "";
            var embeddedBitmapData:BitmapData;

            embeddedBitmapData = getEmbeddedMarkerIconBitmapData(normalizedType);
            if (embeddedBitmapData != null) {
                return embeddedBitmapData;
            }

            if (_markerIconBitmapByType.hasOwnProperty(normalizedType)) {
                return _markerIconBitmapByType[normalizedType] as BitmapData;
            }

            if (_markerIconLoadStateByType[normalizedType] === "failed") {
                return null;
            }

            if (_markerIconLoadStateByType[normalizedType] !== "loading") {
                beginMarkerIconLoad(normalizedType, paths);
            }

            return null;
        }

        private function beginMarkerIconLoad(iconKey:String, paths:Array):void {
            if (paths == null || paths.length == 0) {
                _markerIconLoadStateByType[iconKey] = "failed";
                return;
            }

            _markerIconLoadStateByType[iconKey] = "loading";
            loadMarkerIconCandidate(iconKey, paths, 0);
        }

        private function loadMarkerIconCandidate(iconKey:String, paths:Array, pathIndex:int):void {
            var path:String;
            var loader:Loader;
            var onComplete:Function;
            var onError:Function;

            if (paths == null || pathIndex >= paths.length) {
                _markerIconLoadStateByType[iconKey] = "failed";
                return;
            }

            path = String(paths[pathIndex]);
            loader = new Loader();

            onComplete = function(event:Event):void {
                var loadedBitmap:Bitmap = loader.content as Bitmap;

                loader.contentLoaderInfo.removeEventListener(Event.COMPLETE, onComplete);
                loader.contentLoaderInfo.removeEventListener(IOErrorEvent.IO_ERROR, onError);

                if (loadedBitmap != null && loadedBitmap.bitmapData != null) {
                    _markerIconBitmapByType[iconKey] = loadedBitmap.bitmapData.clone();
                    _markerIconLoadStateByType[iconKey] = "ready";
                    try {
                        loader.unload();
                    }
                    catch (error:Error) {
                    }
                    if (_isReady && _context != null) {
                        updateBarFromContext(false);
                    }
                    return;
                }

                try {
                    loader.unload();
                }
                catch (error2:Error) {
                }
                loadMarkerIconCandidate(iconKey, paths, pathIndex + 1);
            };

            onError = function(event:IOErrorEvent):void {
                loader.contentLoaderInfo.removeEventListener(Event.COMPLETE, onComplete);
                loader.contentLoaderInfo.removeEventListener(IOErrorEvent.IO_ERROR, onError);
                try {
                    loader.unload();
                }
                catch (error:Error) {
                }
                loadMarkerIconCandidate(iconKey, paths, pathIndex + 1);
            };

            loader.contentLoaderInfo.addEventListener(Event.COMPLETE, onComplete, false, 0, true);
            loader.contentLoaderInfo.addEventListener(IOErrorEvent.IO_ERROR, onError, false, 0, true);

            try {
                loader.load(new URLRequest(path));
            }
            catch (error:Error) {
                loader.contentLoaderInfo.removeEventListener(Event.COMPLETE, onComplete);
                loader.contentLoaderInfo.removeEventListener(IOErrorEvent.IO_ERROR, onError);
                loadMarkerIconCandidate(iconKey, paths, pathIndex + 1);
            }
        }

        private function resolveMarkerIconKey(marker:Object):String {
            var customPaths:Array = marker != null && marker.iconPaths is Array ? marker.iconPaths as Array : null;
            var cacheKey:String;
            var itemType:String;

            if (customPaths != null && customPaths.length > 0) {
                if (marker != null && marker.iconCacheKey !== undefined && marker.iconCacheKey != null) {
                    cacheKey = String(marker.iconCacheKey);
                    if (cacheKey.length > 0) {
                        return cacheKey;
                    }
                }
                return "custom:" + customPaths.join("|");
            }

            itemType = marker != null && marker.itemType !== undefined ? String(marker.itemType) : "";
            return itemType;
        }

        private function resolveMarkerIconPaths(marker:Object):Array {
            var combined:Array = [];
            var customPaths:Array = marker != null && marker.iconPaths is Array ? marker.iconPaths as Array : null;
            var itemType:String = marker != null && marker.itemType !== undefined ? String(marker.itemType) : "";
            var fallbackPaths:Array = getMarkerIconPaths(itemType);
            var i:int;

            if (customPaths != null) {
                for (i = 0; i < customPaths.length; i++) {
                    combined.push(customPaths[i]);
                }
            }

            if (fallbackPaths != null) {
                for (i = 0; i < fallbackPaths.length; i++) {
                    combined.push(fallbackPaths[i]);
                }
            }

            return combined.length > 0 ? combined : null;
        }

        private function getMarkerIconPaths(itemType:String):Array {
            if (itemType == null || itemType.length == 0 || !MARKER_ICON_PATHS.hasOwnProperty(itemType)) {
                return null;
            }

            return MARKER_ICON_PATHS[itemType] as Array;
        }

        private function drawMask(shape:Shape, posX:Number, posY:Number, width:Number, height:Number):void {
            shape.graphics.clear();
            if (width <= 0 || height <= 0) {
                return;
            }
            shape.graphics.beginFill(0xFFFFFF, 1.0);
            shape.graphics.drawRect(posX, posY, width, height);
            shape.graphics.endFill();
        }

        private function layoutFromStage():void {
            var leftEdge:Number;
            var rightEdge:Number;
            var sideInset:Number;
            var maxWidth:Number;

            x = 0;
            y = 0;
            if (stage == null) {
                _barX = SIDE_MARGIN;
                _barY = TOP_MARGIN;
                _barWidth = MIN_BAR_WIDTH;
                return;
            }

            sideInset = resolveSideSafeInset();
            leftEdge = sideInset;
            rightEdge = Math.round(stage.stageWidth - sideInset);

            if (rightEdge <= leftEdge + MIN_BAR_WIDTH) {
                leftEdge = BAR_MIN_STAGE_SIDE_MARGIN;
                rightEdge = stage.stageWidth - BAR_MIN_STAGE_SIDE_MARGIN;
            }

            _barX = Math.max(0, Math.round(leftEdge));
            maxWidth = Math.max(MIN_BAR_WIDTH, stage.stageWidth - _barX - BAR_MIN_STAGE_SIDE_MARGIN);
            _barWidth = clamp(Math.round(rightEdge - _barX), MIN_BAR_WIDTH, maxWidth);
            _barY = resolveBarTopFromStage();
        }

        private function resolveSideSafeInset():Number {
            return resolveRightRailCutoff() + BAR_SIDE_SAFE_OFFSET;
        }

        private function resolveLayoutDistanceBucket():Object {
            var bucket:Object;

            if (stage == null) {
                return LAYOUT_DISTANCE_BUCKETS[LAYOUT_DISTANCE_BUCKETS.length - 1];
            }

            for each (bucket in LAYOUT_DISTANCE_BUCKETS) {
                if (stage.stageWidth >= Number(bucket.minWidth)) {
                    return bucket;
                }
            }

            return LAYOUT_DISTANCE_BUCKETS[LAYOUT_DISTANCE_BUCKETS.length - 1];
        }

        private function resolveRightRailCutoff():Number {
            return Number(resolveLayoutDistanceBucket().horizontalDistance);
        }

        private function resolveBarTopFromStage():Number {
            var fallbackTop:Number;
            var centeredAssemblyTop:Number;
            var centeredBarTop:Number;
            var fightButtonBounds:Rectangle;
            var maxBarTop:Number;

            if (stage == null) {
                return TOP_MARGIN;
            }

            maxBarTop = Math.max(0, stage.stageHeight - BAR_HEIGHT - BAR_ASSEMBLY_BELOW_HEIGHT);
            fallbackTop = clamp(Math.round(stage.stageHeight * BAR_DEFAULT_TOP_RATIO), BAR_ASSEMBLY_ABOVE_HEIGHT, maxBarTop);
            fightButtonBounds = resolveFightButtonBounds();
            if (fightButtonBounds == null) {
                return fallbackTop;
            }

            centeredAssemblyTop = fightButtonBounds.bottom + Math.round((resolveVerticalBoundaryOffset() - BAR_ASSEMBLY_HEIGHT) * 0.5);
            centeredBarTop = centeredAssemblyTop + BAR_ASSEMBLY_ABOVE_HEIGHT;
            return clamp(centeredBarTop, BAR_ASSEMBLY_ABOVE_HEIGHT, maxBarTop);
        }

        private function resolveVerticalBoundaryOffset():Number {
            return Number(resolveLayoutDistanceBucket().verticalDistance);
        }

        private function resolveFightButtonBounds():Rectangle {
            if (stage == null) {
                return null;
            }

            return findFightButtonBounds(stage);
        }

        private function findFightButtonBounds(container:DisplayObjectContainer):Rectangle {
            var childCount:int;
            var idx:int;
            var child:DisplayObject;
            var bounds:Rectangle;
            var childContainer:DisplayObjectContainer;

            if (container == null) {
                return null;
            }

            try {
                childCount = container.numChildren;
            } catch (error:Error) {
                return null;
            }

            for (idx = 0; idx < childCount; idx++) {
                try {
                    child = container.getChildAt(idx);
                } catch (error:Error) {
                    continue;
                }

                if (child == null || isOwnDisplayTree(child) || !child.visible || child.alpha <= 0.0) {
                    continue;
                }

                if (isFightButtonDisplay(child)) {
                    bounds = safeGetStageBounds(child);
                    if (bounds != null) {
                        return bounds;
                    }
                }

                childContainer = child as DisplayObjectContainer;
                if (childContainer != null) {
                    bounds = findFightButtonBounds(childContainer);
                    if (bounds != null) {
                        return bounds;
                    }
                }
            }

            return null;
        }

        private function isFightButtonDisplay(display:DisplayObject):Boolean {
            var className:String = shortClassName(getQualifiedClassName(display)).toLowerCase();
            var displayName:String = display.name != null ? String(display.name).toLowerCase() : "";

            return displayName.indexOf("fightbutton") >= 0
                || displayName.indexOf("battlebutton") >= 0
                || displayName == "fightbutton_hintarea"
                || (className.indexOf("tutorialhintzone") >= 0 && displayName.indexOf("hintarea") >= 0 && displayName.indexOf("fight") >= 0);
        }

        private function safeGetStageBounds(display:DisplayObject):Rectangle {
            var bounds:Rectangle;

            if (display == null || stage == null) {
                return null;
            }

            try {
                bounds = display.getBounds(stage);
            } catch (error:Error) {
                return null;
            }

            if (bounds == null || bounds.width < 8 || bounds.height < 8) {
                return null;
            }
            if (bounds.right < 0 || bounds.bottom < 0 || bounds.x > stage.stageWidth || bounds.y > stage.stageHeight) {
                return null;
            }
            if (bounds.width >= stage.stageWidth - 2 && bounds.height >= stage.stageHeight - 2) {
                return null;
            }

            return bounds;
        }

        private function isOwnDisplayTree(display:DisplayObject):Boolean {
            var current:DisplayObject = display;

            while (current != null) {
                if (current == this) {
                    return true;
                }
                current = current.parent;
            }

            return false;
        }

        private function shortClassName(value:String):String {
            var separator:int = value.lastIndexOf("::");
            if (separator >= 0) {
                return value.substring(separator + 2);
            }
            return value;
        }

        private function positionLabels():void {
            var counterTop:Number = _barY + BAR_HEIGHT + 1 + COUNTER_TOP_OFFSET;
            var leftCounterX:Number = _barX - LEFT_COUNTER_OFFSET;
            var rightCounterEdge:Number = _barX + _barWidth;

            if (_activeCounterLayout == COUNTER_LAYOUT_RIGHT_SINGLE) {
                positionRightCounterGroup(totalPercentLabel, totalPercentCaption, rightCounterEdge, counterTop);
                return;
            }

            if (_activeCounterLayout == COUNTER_LAYOUT_ELITE_STATUS) {
                combatPercentLabel.x = leftCounterX;
                combatPercentLabel.y = counterTop;

                combatPercentCaption.x = leftCounterX;
                combatPercentCaption.y = counterTop + combatPercentLabel.height;

                positionRightCounterGroup(totalPercentLabel, totalPercentCaption, rightCounterEdge, counterTop);
                return;
            }

            if (hasCounterText(sideCounterLabel) || hasCounterText(sideCounterCaption)) {
                positionLeftCounterGroup(sideCounterLabel, sideCounterCaption, leftCounterX, counterTop);
            }

            positionRightCounterGroup(combatPercentLabel, combatPercentCaption, rightCounterEdge, counterTop);
            positionRightCounterGroup(totalPercentLabel, totalPercentCaption, rightCounterEdge, counterTop + combatPercentLabel.height);
        }

        private function positionLeftCounterGroup(valueField:TextField, captionField:TextField, groupX:Number, groupY:Number):void {
            var valueWidth:Number = resolveDisplayTextWidth(valueField);
            var captionWidth:Number = hasCounterText(captionField) ? resolveDisplayTextWidth(captionField) : 0;

            valueField.width = valueWidth;
            valueField.x = groupX;
            valueField.y = groupY;

            if (captionField != null) {
                captionField.width = captionWidth;
                captionField.x = groupX + valueWidth + (captionWidth > 0 ? COUNTER_TEXT_GAP : 0);
                captionField.y = groupY;
            }
        }

        private function positionRightCounterGroup(valueField:TextField, captionField:TextField, rightEdge:Number, groupY:Number):void {
            var captionWidth:Number = hasCounterText(captionField) ? COUNTER_CAPTION_WIDTH : 0;

            valueField.width = COUNTER_VALUE_WIDTH;
            valueField.x = rightEdge - COUNTER_VALUE_WIDTH + RIGHT_COUNTER_VALUE_OFFSET;
            valueField.y = groupY;

            if (captionField != null) {
                captionField.width = captionWidth;
                captionField.x = valueField.x - (captionWidth > 0 ? COUNTER_TEXT_GAP + COUNTER_CAPTION_WIDTH : 0);
                captionField.y = groupY;
            }
        }

        private function resolveDisplayTextWidth(field:TextField):Number {
            if (field == null || field.text == null || field.text.length == 0) {
                return 0;
            }

            return Math.max(1, Math.ceil(field.textWidth + 4));
        }

        private function positionCounterGroup(valueField:TextField, captionField:TextField, groupX:Number, groupY:Number):void {
            valueField.x = groupX;
            valueField.y = groupY;

            if (captionField != null) {
                captionField.x = groupX + COUNTER_VALUE_WIDTH + (hasCounterText(captionField) ? COUNTER_TEXT_GAP : 0);
                captionField.y = groupY;
            }
        }

        private function measureCounterGroupWidth(captionField:TextField):Number {
            if (captionField != null && hasCounterText(captionField)) {
                return COUNTER_VALUE_WIDTH + COUNTER_TEXT_GAP + COUNTER_CAPTION_WIDTH;
            }

            return COUNTER_VALUE_WIDTH;
        }

        private function hasCounterText(field:TextField):Boolean {
            return field != null && field.text != null && field.text.length > 0;
        }

        private function resolveCenteredTextY(field:TextField, containerTop:Number, containerHeight:Number):Number {
            return containerTop + Math.round((containerHeight - field.textHeight) / 2) - 2;
        }

        private function createBitmap(assetClass:Class):Bitmap {
            var bitmap:Bitmap = new assetClass() as Bitmap;
            bitmap.smoothing = true;
            return bitmap;
        }

        private function numberValue(value:*, fallback:Number):Number {
            var parsed:Number = Number(value);
            if (isNaN(parsed)) {
                return fallback;
            }
            return parsed;
        }

        private function clamp(value:Number, minValue:Number, maxValue:Number):Number {
            if (value < minValue) {
                return minValue;
            }
            if (value > maxValue) {
                return maxValue;
            }
            return value;
        }

        private function makeMarkerLabelField(text:String, markerTopY:Number):TextField {
            var field:TextField = makeTextField(LABEL_COLOR, 16, true);
            alignTextField(field, TextFormatAlign.CENTER);
            field.width = 48;
            field.height = 22;
            field.x = -24;
            field.y = markerTopY - field.height;
            field.text = text;
            return field;
        }

        private function makeCounterField():TextField {
            var field:TextField = makeTextField(LABEL_COLOR, COUNTER_FONT_SIZE, true);
            alignTextField(field, TextFormatAlign.RIGHT);
            field.width = COUNTER_VALUE_WIDTH;
            field.height = COUNTER_FIELD_HEIGHT;
            return field;
        }

        private function makeCounterCaptionField(text:String):TextField {
            var field:TextField = makeTextField(MARKER_VALUE_COLOR, COUNTER_FONT_SIZE, false);
            alignTextField(field, TextFormatAlign.LEFT);
            field.width = COUNTER_CAPTION_WIDTH;
            field.height = COUNTER_FIELD_HEIGHT;
            field.text = text;
            return field;
        }

        private function alignTextField(field:TextField, alignment:String):void {
            var format:TextFormat = field.defaultTextFormat;

            format.align = alignment;
            field.defaultTextFormat = format;
            field.setTextFormat(format);
        }

        private function formatExactXpValue(value:Number):String {
            var integerValue:int = Math.round(value);
            var text:String = Math.abs(integerValue).toString();
            var parts:Array = [];

            while (text.length > 3) {
                parts.unshift(text.substr(text.length - 3));
                text = text.substr(0, text.length - 3);
            }

            if (text.length > 0) {
                parts.unshift(text);
            }

            text = parts.join(" ");
            if (integerValue < 0) {
                text = "-" + text;
            }

            return text;
        }

        private function formatCompactValue(value:Number, suffix:String):String {
            var absValue:Number = Math.abs(value);
            var decimals:int;
            var precision:Number;
            var rounded:Number;
            var text:String;

            if (absValue < 10) {
                decimals = 2;
            }
            else if (absValue < 100) {
                decimals = 1;
            }
            else {
                decimals = 0;
            }

            precision = Math.pow(10, decimals);
            rounded = Math.round(value * precision) / precision;
            text = rounded.toFixed(decimals);

            while (text.indexOf(".") != -1 && (text.charAt(text.length - 1) == "0" || text.charAt(text.length - 1) == ".")) {
                text = text.substr(0, text.length - 1);
            }

            return text + suffix;
        }

        private function makeTextField(color:uint, size:int, bold:Boolean):TextField {
            var field:TextField = new TextField();
            field.defaultTextFormat = new TextFormat("_sans", size, color, bold);
            field.selectable = false;
            field.mouseEnabled = false;
            field.textColor = color;
            field.multiline = false;
            field.wordWrap = false;
            return field;
        }
    }
}
