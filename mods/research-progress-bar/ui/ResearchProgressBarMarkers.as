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
        // Clear space kept between two bar icons once they have been spread apart.
        private static const MARKER_ICON_SPREAD_GAP:Number = 2;

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
            onMarkerMouseOut:Function,
            onMarkerClick:Function
        ):Dictionary {
            var marker:Object;
            var markerPositionValue:Number;
            var markerTooltipValue:Number;
            var markerX:Number;
            var markerDisplay:Sprite;
            var markerIcon:Bitmap;
            var iconEntries:Array = [];
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
                    onMarkerMouseOut,
                    onMarkerClick
                );
                markerDisplay.x = barX + markerX;
                markerDisplay.y = barY;
                updateMarkerHitArea(markerDisplay);
                container.addChild(markerDisplay);
                markerIcon = markerIconOf(markerDisplay);
                if (markerIcon != null) {
                    // Wanted centre is the marker's own x: the icon is drawn centred
                    // on it until the spread pass moves it.
                    iconEntries.push({
                        display: markerDisplay,
                        icon: markerIcon,
                        desired: markerDisplay.x,
                        width: markerIcon.width
                    });
                }
                tooltipDataByDisplay[markerDisplay] = {
                    marker: marker,
                    costXp: markerTooltipValue,
                    combatXp: combatXp,
                    freeXp: freeXp
                };
            }

            spreadMarkerIcons(iconEntries);
            return tooltipDataByDisplay;
        }

        // The bar icon of a marker, or null when it has none. Child 0 is always the
        // marker dot; child 1, when present and a Bitmap, is the bar icon (a TextField
        // there is the level label instead -- see createMarkerDisplay).
        private static function markerIconOf(markerDisplay:Sprite):Bitmap {
            if (markerDisplay == null || markerDisplay.numChildren < 2) {
                return null;
            }
            return markerDisplay.getChildAt(1) as Bitmap;
        }

        // Spreads bar icons sideways so they stop overlapping, preserving their
        // left-to-right order and moving them as little as possible.
        //
        // Fanning each cluster out on its own does not work: spreading one cluster can
        // push it into its neighbour, and resolving that can push into a third. This
        // is a pool-adjacent-violators pass instead -- icons are placed left to right,
        // and whenever the block being placed still collides with the previous one the
        // two are merged into a single block re-centred on the mean of its members'
        // wanted positions. That re-check cascades left, so two neighbouring clusters
        // that would collide after spreading simply become one evenly spread block.
        // Only the icons move; the marker dots stay on their true XP positions.
        private static function spreadMarkerIcons(entries:Array):void {
            var blocks:Array = [];
            var entry:Object;
            var block:Object;
            var rels:Array;
            var base:Number;
            var idx:int;

            if (entries == null || entries.length < 2) {
                return;
            }

            entries.sort(compareIconEntries);

            for each (entry in entries) {
                blocks.push({items: [entry]});
                while (blocks.length > 1
                        && blocksCollide(blocks[blocks.length - 2], blocks[blocks.length - 1])) {
                    block = blocks.pop();
                    blocks[blocks.length - 1] = {
                        items: (blocks[blocks.length - 1].items as Array).concat(block.items)
                    };
                }
            }

            for each (block in blocks) {
                rels = blockOffsets(block);
                base = blockBase(block, rels);
                for (idx = 0; idx < block.items.length; idx++) {
                    entry = block.items[idx];
                    // icon.x is local to its marker sprite and addresses the icon's
                    // left edge, so convert the wanted absolute centre back.
                    entry.icon.x = Math.round(base + rels[idx] - entry.display.x - entry.width / 2);
                    // The hit area is derived from the sprite's bounds, so re-run it to
                    // take in the icon's new position -- the icon stays hoverable where
                    // it is actually drawn.
                    updateMarkerHitArea(entry.display);
                }
            }
        }

        private static function compareIconEntries(a:Object, b:Object):Number {
            return Number(a.desired) - Number(b.desired);
        }

        // Centre offsets of a block's icons relative to its first icon, packed edge to
        // edge with MARKER_ICON_SPREAD_GAP between them (widths may differ).
        private static function blockOffsets(block:Object):Array {
            var items:Array = block.items as Array;
            var offsets:Array = [0];
            var idx:int;

            for (idx = 1; idx < items.length; idx++) {
                offsets.push(
                    Number(offsets[idx - 1])
                        + (Number(items[idx - 1].width) + Number(items[idx].width)) / 2
                        + MARKER_ICON_SPREAD_GAP
                );
            }
            return offsets;
        }

        // Where a block's first icon sits so the block as a whole deviates least from
        // what its members wanted (the mean of each wanted centre minus its offset).
        private static function blockBase(block:Object, offsets:Array):Number {
            var items:Array = block.items as Array;
            var total:Number = 0;
            var idx:int;

            for (idx = 0; idx < items.length; idx++) {
                total += Number(items[idx].desired) - Number(offsets[idx]);
            }
            return total / items.length;
        }

        private static function blocksCollide(left:Object, right:Object):Boolean {
            var leftOffsets:Array = blockOffsets(left);
            var rightOffsets:Array = blockOffsets(right);
            var leftItems:Array = left.items as Array;
            var rightItems:Array = right.items as Array;
            var leftEnd:Number = blockBase(left, leftOffsets)
                + Number(leftOffsets[leftOffsets.length - 1])
                + Number(leftItems[leftItems.length - 1].width) / 2;
            var rightStart:Number = blockBase(right, rightOffsets)
                + Number(rightOffsets[0])
                - Number(rightItems[0].width) / 2;

            return leftEnd + MARKER_ICON_SPREAD_GAP > rightStart;
        }

        private static function createMarkerDisplay(
            marker:Object,
            markerProgressValue:Number,
            combatXp:Number,
            freeXp:Number,
            onMarkerMouseOver:Function,
            onMarkerMouseOut:Function,
            onMarkerClick:Function
        ):Sprite {
            var markerSprite:Sprite = new Sprite();
            var markerBitmap:Bitmap = createMarkerBitmap(marker, markerProgressValue, combatXp, freeXp);
            var markerIcon:Bitmap;
            var markerLabel:TextField;

            markerBitmap.x = -Math.round(markerBitmap.width / 2);
            markerBitmap.y = -Math.round((markerBitmap.height - ResearchProgressBarLayout.BAR_HEIGHT) / 2);
            markerSprite.addChild(markerBitmap);

            markerIcon = createMarkerIcon(marker, markerBitmap.y, markerProgressValue, combatXp, freeXp);
            if (markerIcon != null) {
                markerSprite.addChild(markerIcon);
            }
            else if (shouldShowMarkerLabel(marker)) {
                markerLabel = makeMarkerLabelField(marker, markerBitmap.y, markerProgressValue, combatXp, freeXp);
                markerSprite.addChild(markerLabel);
            }

            markerSprite.mouseEnabled = true;
            markerSprite.mouseChildren = false;
            // Keep markers out of keyboard focus/tab traversal. Click focus is
            // handled defensively in clearMarkers (GFx has no mouseFocusEnabled).
            markerSprite.tabEnabled = false;
            markerSprite.focusRect = false;
            markerSprite.addEventListener(MouseEvent.MOUSE_OVER, onMarkerMouseOver, false, 0, true);
            markerSprite.addEventListener(MouseEvent.MOUSE_OUT, onMarkerMouseOut, false, 0, true);
            if (onMarkerClick != null
                    && ResearchProgressBarInteractions.isMarkerClickable(marker, combatXp, freeXp)
                    && !isPickMarker(marker)) {
                // buttonMode + useHandCursor make GFx dispatch a CURSOR_CHANGE that
                // WoT's CursorManager forwards to the engine cursor (the hand).
                // Pick markers (dual A/B choice) are excluded: a mouse click can't
                // express which option, and WoT's hangar GFx delivers no usable
                // right-click, so they are keyboard-driven instead (press 1/2, see
                // ResearchProgressBarLobby.onStageKeyDown).
                markerSprite.buttonMode = true;
                markerSprite.useHandCursor = true;
                markerSprite.addEventListener(MouseEvent.CLICK, onMarkerClick, false, 0, true);
            }
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
            // The dot and its icon share one colour state so they can never disagree.
            switch (ResearchProgressBarIconTint.resolveState(marker, markerProgressValue, combatXp, freeXp)) {
                case "completed":
                    return createBitmap(MarkerWhiteAsset);
                case "vehicle":
                    return createBitmap(MarkerGreenAsset);
                case "total":
                    return createBitmap(MarkerYellowAsset);
                default:
                    return createBitmap(MarkerDefaultAsset);
            }
        }

        private static function createMarkerIcon(marker:Object, markerTopY:Number, markerProgressValue:Number, combatXp:Number, freeXp:Number):Bitmap {
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
            // Recolour the greyscale icon to its marker's state, matching the dot.
            // The prestige badges keep their own colours and pass through untinted.
            if (ResearchProgressBarMarkerAssets.isMarkerBarIconTintable(marker)) {
                ResearchProgressBarIconTint.applyColor(
                    icon,
                    ResearchProgressBarIconTint.colorForMarker(marker, markerProgressValue, combatXp, freeXp)
                );
            }
            icon.x = -Math.round(icon.width / 2);
            icon.y = markerTopY - MARKER_ICON_GAP - icon.height;
            return icon;
        }

        private static function isPickMarker(marker:Object):Boolean {
            return marker != null
                && marker.clickAction != null
                && marker.clickAction.leftId !== undefined
                && marker.clickAction.rightId !== undefined;
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

        private static function makeMarkerLabelField(marker:Object, markerTopY:Number, markerProgressValue:Number, combatXp:Number, freeXp:Number):TextField {
            var labelHtml:String = marker != null && marker.labelHtml !== undefined && marker.labelHtml != null
                ? String(marker.labelHtml)
                : "";
            var labelText:String = marker != null && marker.label !== undefined && marker.label != null
                ? String(marker.label)
                : "";
            // Field-mod markers show a level label instead of an icon; colour it to the
            // marker's state, the same as the icons and the dash beneath it.
            var labelColor:uint = ResearchProgressBarIconTint.colorForMarker(marker, markerProgressValue, combatXp, freeXp);
            var field:TextField;

            if (labelHtml.length > 0) {
                field = makeTextField(labelColor, 16, false);
                ResearchProgressBarFonts.setHtmlText(field, labelHtml);
            }
            else {
                field = makeTextField(labelColor, 16, true);
                ResearchProgressBarFonts.setText(field, labelText);
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