SELECT DISTINCT
    rtb.AdvertiserId
    ,adv.AdvertiserName
    ,rtb.CampaignId
    ,cp.CampaignName
FROM
    reports.RTBPlatformReport rtb
    LEFT OUTER JOIN provisioning2.Advertiser adv
        ON rtb.AdvertiserId = adv.AdvertiserId
    LEFT OUTER JOIN provisioning2.Campaign cp
        ON rtb.CampaignId = cp.CampaignId
WHERE 1=1
    AND (
            (ReportHourUtc >= ('{StartDate}'::timestamp at timezone 'Asia/Tokyo')::timestamp)
            AND
            (ReportHourUtc < ('{EndDate}'::timestamp at timezone 'Asia/Tokyo')::timestamp)
        )
    AND rtb.AdvertiserId IN ('{AdvertiserId}')
ORDER BY
    cp.CampaignName
