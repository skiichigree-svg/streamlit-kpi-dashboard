WITH

raw_data AS (
    SELECT
        EXTRACT(YEAR FROM (perf.ReportHourUtc::timestamptz AT TIME ZONE 'JST'))::INT AS "year"
        ,EXTRACT(MONTH FROM (perf.ReportHourUtc::timestamptz AT TIME ZONE 'JST'))::INT AS "month"
        ,EXTRACT(QUARTER FROM (perf.ReportHourUtc::timestamptz AT TIME ZONE 'JST'))::INT AS "quarter"
        ,DATE(perf.ReportHourUtc::timestamptz AT TIME ZONE 'JST') AS "jst_date"
        ,perf.PartnerId
        ,prt.PartnerName
        ,perf.AdvertiserId
        ,adv.AdvertiserName
        ,perf.CampaignId
        ,cp.CampaignName
        ,perf.AdGroupId
        ,adg.AdGroupName
        ,CASE
            WHEN LOWER(adg.AdGroupName) LIKE '%abema%' THEN 'ABEMA'
            WHEN (LOWER(adg.AdGroupName) LIKE '%tver%' OR LOWER(adg.AdGroupName) LIKE '%openpath%') THEN 'TVer'
            WHEN LOWER(adg.AdGroupName) LIKE '%hulu%' THEN 'Hulu'
            WHEN LOWER(adg.AdGroupName) LIKE '%sp500%' THEN 'SP500+'
            WHEN LOWER(adg.AdGroupName) LIKE '%dazn%' THEN 'DAZN'
            WHEN LOWER(adg.AdGroupName) LIKE '%netflix%' THEN 'Netflix'
            WHEN LOWER(adg.AdGroupName) LIKE '%niconico%' THEN 'niconico'
            WHEN LOWER(adg.AdGroupName) LIKE '%spotv%' THEN 'Spotv'
            WHEN LOWER(adg.AdGroupName) LIKE '%gyao%' THEN 'GyaO'
            WHEN LOWER(adg.AdGroupName) LIKE '%radiko%' THEN 'Radiko'
            WHEN LOWER(adg.AdGroupName) LIKE '%spotify%' THEN 'Spotify'
            WHEN LOWER(adg.AdGroupName) LIKE '%gumgum%' THEN 'GumGum'
            WHEN LOWER(adg.AdGroupName) LIKE '%ogury%' THEN 'Ogury'
            WHEN (LOWER(adg.AdGroupName) LIKE '%open%' AND LOWER(adg.AdGroupName) NOT LIKE '%openpath%') THEN 'Open'
            WHEN LOWER(adg.AdGroupName) LIKE '%smartnews%' THEN 'SmartNews'
            WHEN LOWER(adg.AdGroupName) LIKE '%teads%' THEN 'Teads'
            WHEN LOWER(adg.AdGroupName) LIKE '%fluct%' THEN 'Fluct'
            WHEN LOWER(cp.CampaignName) LIKE '%tver%' THEN 'TVer'
            WHEN LOWER(cp.CampaignName) LIKE '%spotify%' THEN 'Spotify'
            WHEN LOWER(cp.CampaignName) LIKE '%netflix%' THEN 'Netflix'
            WHEN LOWER(cp.CampaignName) LIKE '%fluct%' THEN 'Fluct'
            WHEN (LOWER(cp.CampaignName) LIKE '%open%' AND LOWER(cp.CampaignName) NOT LIKE '%openpath%') THEN 'Open'
            WHEN perf.CampaignId = 'vabgxl2' THEN 'LiveBoard'
            WHEN perf.CampaignId = 'ko5kniv' THEN 'Spotify'
            WHEN perf.CampaignId = 'zs6s97b' THEN 'Netflix'
            WHEN perf.CampaignId = 'x2pxtq7' THEN 'Netflix'
            WHEN (
                perf.CampaignId = '8jtt3a6'
                    OR perf.CampaignId = 'mcrqb9j'
                    OR perf.CampaignId = 'vzaaxmv'
                    OR perf.CampaignId = 'y5ui15v'
                    OR perf.CampaignId = 'x1k2lh9'
                    OR perf.CampaignId = 'raghqgj'
                    OR perf.CampaignId = 'o6se3i5'
                    OR perf.CampaignId = 'fdlh752'
                    OR perf.CampaignId = 'u3aadut'
                    OR perf.CampaignId = 'cyws4r1'
                    OR perf.CampaignId = 'tssdwql'
                    OR perf.CampaignId = 'gly3o2n'
                    OR perf.CampaignId = 'snbbzep'
                    OR perf.CampaignId = '4m7h384'
                    OR perf.CampaignId = 'g728m0q'
                    OR perf.CampaignId = 'rrjk003'
                    OR perf.CampaignId = 'zytlcky'
                )THEN 'TVer'
            WHEN perf.CampaignId = '1dqtffj' THEN 'Spotify'
            WHEN perf.CampaignId = 'e5eqgoo' THEN 'Spotify'
            WHEN perf.CampaignId = 'bl0t8qv' THEN 'Spotify'
            WHEN perf.CampaignId = '0s8r64e' THEN 'niconico'
            WHEN perf.CampaignId = 'eaudvia' THEN 'SP500+'
            ELSE 'Not specified'
        END AS "Media"
        ,ChannelId
        ,d.DeviceTypeName
        ,ttd.fn_GetMarketType(MarketplaceName, perf.DealId) as "MarketType"
        ,SUM(AdvertiserCostInAdvertiserCurrency) AS AdvertiserCostInAdvertiserCurrency
        ,SUM(AdvertiserCostInUSD) AS AdvertiserCostInUSD
        ,SUM(PartnerCostInAdvertiserCurrency) AS PartnerCostInAdvertiserCurrency
        ,SUM(PartnerCostInUSD) AS PartnerCostInUSD
        ,SUM(MediaCostInAdvertiserCurrency) AS MediaCostInAdvertiserCurrency
        ,SUM(MediaCostInUSD) AS MediaCostInUSD
        ,SUM(DataCostInAdvertiserCurrency) AS DataCostInAdvertiserCurrency
        ,SUM(DataCostInUSD) AS DataCostInUSD
        ,SUM(ImpressionCount) AS ImpressionCount
        ,SUM(ClickCount) AS ClickCount
        ,SUM(CustomCPACount) AS CustomCPAConversion
    FROM
        reports.PerformanceReport perf
            LEFT JOIN provisioning2.Partner prt
                ON perf.PartnerId = prt.PartnerId
            LEFT JOIN provisioning2.Advertiser adv
                ON perf.AdvertiserId = adv.AdvertiserId
            LEFT JOIN provisioning2.Campaign cp
                ON perf.CampaignId = cp.CampaignId
            LEFT JOIN provisioning2.AdGroup adg
                ON perf.AdGroupId = adg.AdGroupId
            LEFT JOIN provisioning2.Marketplace m
                ON perf.MarketplaceId = m.MarketplaceId
            LEFT JOIN provisioning2.DeviceType d
                ON perf.DeviceTypeId = d.DeviceTypeId
    WHERE
        perf.PartnerId IN (
            '12otvni', -- CyberAgent JP
            'htocuxo', -- CyberZ JP
            'xy8dnk2'  -- Mixi
            )
        AND perf.ReportHourUTC >= '${StartDate}'::timestamp AT TIME ZONE 'JST'
        AND perf.ReportHourUTC < '${EndDate}'::timestamp AT TIME ZONE 'JST'::date + INTERVAL '1 day'
    GROUP BY
        "year"
        ,"quarter"
        ,"month"
        ,"jst_date"
        ,perf.PartnerId
        ,prt.PartnerName
        ,perf.AdvertiserId
        ,adv.AdvertiserName
        ,perf.CampaignId
        ,cp.CampaignName
        ,perf.AdGroupId
        ,adg.AdGroupName
        ,"Media"
        ,ChannelId
        ,d.DeviceTypeName
        ,"MarketType"
)

SELECT
    r.year
    ,r.quarter
    ,r.month
    ,r.jst_date
    ,r.PartnerId
    ,r.PartnerName
    ,r.AdvertiserId
    ,r.AdvertiserName
    ,r.CampaignId
    ,r.CampaignName
    ,r.AdGroupId
    ,r.AdGroupName
    ,r.Media
    ,CASE
        WHEN r.Media IN (
                       'ABEMA',
                       'DAZN',
                       'GyaO',
                       'Hulu',
                       'Netflix',
                       'Spotv',
                       'TVer'
            ) THEN 'CTV/OTT'
        WHEN EXISTS (
            SELECT 1
            FROM raw_data AS r2
            WHERE r2.CampaignId = r.CampaignId
            AND LOWER(COALESCE(r2.DeviceTypeName, '')) LIKE 'ConnectedTV'
            ) THEN 'CTV/OTT'
    WHEN r.ChannelId = 0 THEN 'Other'
    WHEN r.ChannelId = 1 THEN 'Display'
    WHEN r.ChannelId = 2 THEN 'Video'
    WHEN r.ChannelId = 3 THEN 'Audio'
    WHEN r.ChannelId = 4 THEN 'CTV/TV'
    WHEN r.ChannelId = 5 THEN 'NativeDisplay'
    WHEN r.ChannelId = 6 THEN 'NativeVideo'
    WHEN r.ChannelId = 7 THEN 'OutOfHome'
    END AS "Channel"
    ,r.DeviceTypeName
    ,r.MarketType
    ,r.AdvertiserCostInAdvertiserCurrency
    ,r.AdvertiserCostInUSD
    ,r.PartnerCostInAdvertiserCurrency
    ,r.PartnerCostInUSD
    ,r.MediaCostInAdvertiserCurrency
    ,r.MediaCostInUSD
    ,r.DataCostInAdvertiserCurrency
    ,r.DataCostInUSD
    ,r.ImpressionCount
    ,r.ClickCount
    ,r.CustomCPAConversion
FROM
    raw_data r
ORDER BY
    r.year
    ,r.quarter
    ,r.month
    ,r.jst_date
    ,r.PartnerId
    ,r.PartnerName
    ,r.AdvertiserId
    ,r.AdvertiserName
    ,r.CampaignId
    ,r.CampaignName
    ,r.AdGroupId
    ,r.AdGroupName;
