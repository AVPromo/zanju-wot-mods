package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.Sprite;
    import flash.events.MouseEvent;
    import flash.geom.Rectangle;
    import flash.text.TextField;
    import flash.text.TextFormat;
    import flash.text.TextFormatAlign;
    import flash.utils.Dictionary;

    public final class ResearchProgressBarMarkers {
        [Embed(source="assets/marker_default.png")]
        private static const MarkerDefaultAsset:Class;

        [Embed(source="assets/marker_green.png")]
        private static const MarkerGreenAsset:Class;

        [Embed(source="assets/marker_white.png")]
        private static const MarkerWhiteAsset:Class;

        [Embed(source="assets/marker_yellow.png")]
        private static const MarkerYellowAsset:Class;

        private static const LABEL_COLOR:uint = 0xE6DDC8;
        private static const MARKER_ICON_GAP:Number = 2;

        public static function clearMarkers(container:Sprite):void {
            if (container == null) {
                return;
            }

            while (container.numChildren > 0) {
                container.removeChildAt(0);
            }
        }

        public static function rebuildMarkers(
            container:Sprite,
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
            var marker:Object;
            var markerPositionValue:Number;
            var markerTooltipValue:Number;
            var markerX:Number;
            var markerDisplay:Sprite;
            var tooltipDataByDisplay:Dictionary = new Dictionary(true);

            if (container == null || activeMode == null || !(activeMode.markers is Array)) {
                return tooltipDataByDisplay;
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
                markerTooltipValue = numberValue(
                    marker != null && marker.costXp !== undefined ? marker.costXp : markerPositionValue,
                    markerPositionValue
                );
                markerX = Math.round(barWidth * markerPositionValue / maxRequirementXp);
                markerDisplay = createMarkerDisplay(
                    marker,
                    markerPositionValue,
                    combatXp,
                    freeXp,
                    onMarkerMouseOver,
                    onMarkerMouseOut
                );
                markerDisplay.x = barX + markerX;
                markerDisplay.y = barY;
                updateMarkerHitArea(markerDisplay);
                container.addChild(markerDisplay);
                tooltipDataByDisplay[markerDisplay] = {
                    marker: marker,
                    costXp: markerTooltipValue,
                    combatXp: combatXp,
                    freeXp: freeXp
                };
            }

            return tooltipDataByDisplay;
        }

        private static function createMarkerDisplay(
            marker:Object,
            markerProgressValue:Number,
            combatXp:Number,
            freeXp:Number,
            onMarkerMouseOver:Function,
            onMarkerMouseOut:Function
        ):Sprite {
            var markerSprite:Sprite = new Sprite();
            var markerBitmap:Bitmap = createMarkerBitmap(marker, markerProgressValue, combatXp, freeXp);
            var markerIcon:Bitmap;
            var markerLabel:TextField;

            markerBitmap.x = -Math.round(markerBitmap.width / 2);
            markerBitmap.y = -Math.round((markerBitmap.height - ResearchProgressBarLayout.BAR_HEIGHT) / 2);
            markerSprite.addChild(markerBitmap);

            markerIcon = createMarkerIcon(marker, markerBitmap.y);
            if (markerIcon != null) {
                markerSprite.addChild(markerIcon);
            }
            else if (shouldShowMarkerLabel(marker)) {
                markerLabel = makeMarkerLabelField(marker, markerBitmap.y);
                markerSprite.addChild(markerLabel);
            }

            markerSprite.mouseEnabled = true;
            markerSprite.mouseChildren = false;
            markerSprite.addEventListener(MouseEvent.MOUSE_OVER, onMarkerMouseOver, false, 0, true);
            markerSprite.addEventListener(MouseEvent.MOUSE_OUT, onMarkerMouseOut, false, 0, true);
            return markerSprite;
        }

        private static function updateMarkerHitArea(markerDisplay:Sprite):void {
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

        private static function createMarkerBitmap(marker:Object, markerProgressValue:Number, combatXp:Number, freeXp:Number):Bitmap {
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

        private static function createMarkerIcon(marker:Object, markerTopY:Number):Bitmap {
            var bitmapData:BitmapData;
            var icon:Bitmap;

            if (shouldHideBarIcon(marker)) {
                return null;
            }

            bitmapData = ResearchProgressBarMarkerAssets.getMarkerBarIconBitmapDataForMarker(marker);
            if (bitmapData == null) {
                return null;
            }

            icon = new Bitmap(bitmapData);
            icon.smoothing = true;
            icon.x = -Math.round(icon.width / 2);
            icon.y = markerTopY - MARKER_ICON_GAP - icon.height;
            return icon;
        }

        private static function shouldHideBarIcon(marker:Object):Boolean {
            return marker != null && marker.hideBarIcon !== undefined && Boolean(marker.hideBarIcon);
        }

        private static function shouldShowMarkerLabel(marker:Object):Boolean {
            var markerLabel:String;
            var markerLabelHtml:String;

            if (marker == null) {
                return false;
            }

            if (!(marker.showBarLabel !== undefined && Boolean(marker.showBarLabel))) {
                return false;
            }

            if (marker.labelHtml !== undefined && marker.labelHtml != null) {
                markerLabelHtml = String(marker.labelHtml);
                if (markerLabelHtml.length > 0) {
                    return true;
                }
            }

            if (marker.label === undefined || marker.label == null) {
                return false;
            }

            markerLabel = String(marker.label);
            return markerLabel.length > 0;
        }

        private static function createBitmap(assetClass:Class):Bitmap {
            var bitmap:Bitmap = new assetClass() as Bitmap;
            bitmap.smoothing = true;
            return bitmap;
        }

        private static function makeMarkerLabelField(marker:Object, markerTopY:Number):TextField {
            var labelHtml:String = marker != null && marker.labelHtml !== undefined && marker.labelHtml != null
                ? String(marker.labelHtml)
                : "";
            var labelText:String = marker != null && marker.label !== undefined && marker.label != null
                ? String(marker.label)
                : "";
            var field:TextField;

            if (labelHtml.length > 0) {
                field = makeTextField(LABEL_COLOR, 16, false);
                field.htmlText = labelHtml;
            }
            else {
                field = makeTextField(LABEL_COLOR, 16, true);
                field.text = labelText;
            }

            alignTextField(field, TextFormatAlign.CENTER);
            field.width = Math.max(16, field.textWidth + 8);
            field.height = field.textHeight + 6;
            field.x = -Math.round(field.width / 2);
            field.y = markerTopY - field.height;
            return field;
        }

        private static function alignTextField(field:TextField, alignment:String):void {
            var format:TextFormat = field.defaultTextFormat;

            format.align = alignment;
            field.defaultTextFormat = format;
            field.setTextFormat(format);
        }

        private static function makeTextField(color:uint, size:int, bold:Boolean):TextField {
            var field:TextField = ResearchProgressBarFonts.configureTextField(new TextField());
            field.defaultTextFormat = new TextFormat(ResearchProgressBarFonts.FONT_NAME, size, color, bold);
            field.selectable = false;
            field.mouseEnabled = false;
            field.textColor = color;
            field.multiline = false;
            field.wordWrap = false;
            return field;
        }

        private static function numberValue(value:*, fallback:Number):Number {
            var parsed:Number = Number(value);
            if (isNaN(parsed)) {
                return fallback;
            }
            return parsed;
        }

        private static function clamp(value:Number, minValue:Number, maxValue:Number):Number {
            if (value < minValue) {
                return minValue;
            }
            if (value > maxValue) {
                return maxValue;
            }
            return value;
        }
    }
}