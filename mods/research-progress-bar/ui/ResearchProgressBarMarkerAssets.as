package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;

    public final class ResearchProgressBarMarkerAssets {
        [Embed(source="assets/star.png")]
        private static const T11StarAsset:Class;

        [Embed(source="assets/circle.png")]
        private static const T11MinorUpgradeAsset:Class;

        [Embed(source="assets/rhomb.png")]
        private static const T11MajorUpgradeAsset:Class;

        [Embed(source="assets/research_gun.png")]
        private static const ResearchGunAsset:Class;

        [Embed(source="assets/research_turret.png")]
        private static const ResearchTurretAsset:Class;

        [Embed(source="assets/research_engine.png")]
        private static const ResearchEngineAsset:Class;

        [Embed(source="assets/research_track.png")]
        private static const ResearchTrackAsset:Class;

        [Embed(source="assets/research_radio.png")]
        private static const ResearchRadioAsset:Class;

        [Embed(source="assets/research.png")]
        private static const ResearchVehicleAsset:Class;

        [Embed(source="assets/firepower_filter.png")]
        private static const FirepowerFilterAsset:Class;

        [Embed(source="assets/survivability_filter.png")]
        private static const SurvivabilityFilterAsset:Class;

        [Embed(source="assets/mobility_filter.png")]
        private static const MobilityFilterAsset:Class;

        [Embed(source="assets/stealth_filter.png")]
        private static const StealthFilterAsset:Class;

        [Embed(source="assets/prestige_bronze_1.png")]
        private static const PrestigeBronzeAsset:Class;

        [Embed(source="assets/prestige_silver_1.png")]
        private static const PrestigeSilverAsset:Class;

        [Embed(source="assets/prestige_gold_1.png")]
        private static const PrestigeGoldAsset:Class;

        [Embed(source="assets/prestige_enamel_1.png")]
        private static const PrestigeEnamelAsset:Class;

        [Embed(source="assets/prestige.png")]
        private static const PrestigeEliteAsset:Class;

        [Embed(source="assets/style.png")]
        private static const StyleFilterAsset:Class;

        [Embed(source="assets/loadout_switch.png")]
        private static const LoadoutSwitchAsset:Class;

        [Embed(source="assets/role_slot.png")]
        private static const RoleSlotAsset:Class;

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
            role_slot: "Second Slot Category",
            loadout_switch: "Loadout Switch",
            mechanic: "Mechanic Upgrade",
            mechanics: "Mechanic Upgrade",
            minor_upgrade: "Minor Upgrade",
            major_upgrade: "Major Upgrade",
            unknown: "Research Item"
        };

        private static const MARKER_ICON_EMBEDDED:Object = {
            gun: ResearchGunAsset,
            turret: ResearchTurretAsset,
            engine: ResearchEngineAsset,
            suspension: ResearchTrackAsset,
            radio: ResearchRadioAsset,
            vehicle: ResearchVehicleAsset,
            firepower: FirepowerFilterAsset,
            survivability: SurvivabilityFilterAsset,
            mobility: MobilityFilterAsset,
            stealth: StealthFilterAsset,
            reconnaissance: StealthFilterAsset,
            scouting: StealthFilterAsset,
            role_slot: RoleSlotAsset,
            loadout_switch: LoadoutSwitchAsset,
            minor_upgrade: T11MinorUpgradeAsset,
            major_upgrade: T11MajorUpgradeAsset,
            mechanic: T11StarAsset,
            mechanics: T11StarAsset,
            "elite:bronze": PrestigeBronzeAsset,
            "elite:silver": PrestigeSilverAsset,
            "elite:gold": PrestigeGoldAsset,
            "elite:red_gold": PrestigeEnamelAsset,
            "elite:prestige_elite": PrestigeEliteAsset,
            "elite:t11_cosmetic": StyleFilterAsset
        };

        public static function resolveMarkerName(marker:Object):String {
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

        public static function getMarkerBarIconBitmapDataForMarker(marker:Object):BitmapData {
            var barItemType:String;

            barItemType = resolveMarkerBarItemType(marker);
            if (barItemType.length > 0) {
                return getMarkerIconBitmapData(barItemType);
            }

            return getMarkerIconBitmapDataForMarker(marker);
        }

        public static function resolveMarkerBarItemType(marker:Object):String {
            var itemType:String;
            var iconCacheKey:String;
            var cacheParts:Array;

            if (marker == null) {
                return "";
            }

            if (marker.barItemType !== undefined && marker.barItemType != null) {
                return String(marker.barItemType);
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

        public static function getMarkerIconBitmapDataForMarker(marker:Object):BitmapData {
            return getEmbeddedMarkerIconBitmapData(resolveMarkerEmbeddedIconKey(marker));
        }

        public static function getMarkerIconBitmapData(itemType:String):BitmapData {
            return getEmbeddedMarkerIconBitmapData(itemType);
        }

        private static function resolveMarkerEmbeddedIconKey(marker:Object):String {
            var iconCacheKey:String;
            var barItemType:String;
            var itemType:String;

            if (marker == null) {
                return "";
            }

            if (marker.iconCacheKey !== undefined && marker.iconCacheKey != null) {
                iconCacheKey = String(marker.iconCacheKey);
                if (MARKER_ICON_EMBEDDED.hasOwnProperty(iconCacheKey)) {
                    return iconCacheKey;
                }
            }

            barItemType = resolveMarkerBarItemType(marker);
            if (barItemType.length > 0 && MARKER_ICON_EMBEDDED.hasOwnProperty(barItemType)) {
                return barItemType;
            }

            if (marker.itemType !== undefined && marker.itemType != null) {
                itemType = String(marker.itemType);
                if (MARKER_ICON_EMBEDDED.hasOwnProperty(itemType)) {
                    return itemType;
                }
            }

            return "";
        }

        private static function getEmbeddedMarkerIconBitmapData(itemType:String):BitmapData {
            var assetClass:Class;
            var assetBitmap:Bitmap;

            if (itemType == null || !MARKER_ICON_EMBEDDED.hasOwnProperty(itemType)) {
                return null;
            }
            assetClass = MARKER_ICON_EMBEDDED[itemType] as Class;
            if (assetClass == null) {
                return null;
            }
            assetBitmap = new assetClass() as Bitmap;
            if (assetBitmap == null) {
                return null;
            }
            return assetBitmap.bitmapData;
        }
    }
}