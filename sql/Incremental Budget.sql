-- Query for ResultSet 7520868 (Campaign View)

with pte_IBR as (


select
    agf.SnapshotDate
    ,agf.PartnerId
    ,agf.AdvertiserId
    ,agf.CampaignId
    ,agf.CampaignFlightId
    ,agf.AdGroupId
    ,agf.ForecastedSpend
    ,agf.DecisionPower
    ,agf.DailyIncrementalBudgetIdeal
    ,agf.DailyIncrementalBudgetFair
    ,agf.DailyIncrementalBudgetConstrained
    ,agf.ForecastedImpressions
    ,agf.DailyIncrementalImpressionsIdeal
    ,agf.DailyIncrementalImpressionsFair
    ,agf.DailyIncrementalImpressionsConstrained
from reports.AdGroupForecasts agf
inner join provisioning2.CampaignFlight cf on cf.CampaignId = agf.CampaignId and cf.CampaignFlightId = agf.CampaignFlightId
where
    (agf.AdvertiserId in ('8gwz9hf'))
    and agf.SnapshotDate = '2025-07-13'
    and cf.IsCurrent = 1


), cte0 as (
    select
        pte_IBR.AdvertiserId as "Advertiser ID",
        pte_IBR.CampaignId as "Campaign ID",
        pte_IBR.AdGroupId as "Ad Group ID",
        pte_IBR.DecisionPower as "Ad Group Decision Power",
        pte_IBR.CampaignFlightId as "Campaign Flight ID",
        zeroifnull( sum( pte_IBR.ForecastedSpend ) ) as "Ad Group Forecasted Spend (Adv Currency)",
        zeroifnull( sum( pte_IBR.DailyIncrementalBudgetConstrained ) ) as "Daily Incremental Budget (Constrained, Adv Currency)",
        zeroifnull( sum( pte_IBR.DailyIncrementalBudgetFair ) ) as "Daily Incremental Budget (Fair, Adv Currency)",
        zeroifnull( sum( pte_IBR.DailyIncrementalBudgetIdeal ) ) as "Daily Incremental Budget (Ideal, Adv Currency)"
    from
        pte_IBR
    where
        (pte_IBR.AdvertiserId in ('8gwz9hf'))
    group by
        pte_IBR.AdvertiserId,
        pte_IBR.CampaignId,
        pte_IBR.AdGroupId,
        pte_IBR.DecisionPower,
        pte_IBR.CampaignFlightId
),

cteF as (
    select
        adv.AdvertiserName as Advertiser,
        cte0."Advertiser ID" as "Advertiser ID",
        adv.CurrencyCodeId as "Advertiser Currency Code",
        camp.CampaignName as Campaign,
        cte0."Campaign ID" as "Campaign ID",
        ag.AdGroupName as "Ad Group",
        cte0."Ad Group ID" as "Ad Group ID",
        cte0."Ad Group Decision Power" as "Ad Group Decision Power",
        cte0."Campaign Flight ID" as "Campaign Flight ID",
        datediff('day', current_date, cf.EndDateExclusiveUTC::date) as "Days Remaining in Flight",
        cf.BudgetInAdvertiserCurrency as "Campaign Flight Budget (Adv Currency)",
        cf.EndDateExclusiveUTC as "Campaign Flight End Date UTC Exclusive",
        zeroifnull( sum( cte0."Ad Group Forecasted Spend (Adv Currency)" ) ) as "Ad Group Forecasted Spend (Adv Currency)",
        zeroifnull( sum( cte0."Daily Incremental Budget (Constrained, Adv Currency)" ) ) as "Daily Incremental Budget (Constrained, Adv Currency)",
        zeroifnull( sum( cte0."Daily Incremental Budget (Fair, Adv Currency)" ) ) as "Daily Incremental Budget (Fair, Adv Currency)",
        zeroifnull( sum( cte0."Daily Incremental Budget (Ideal, Adv Currency)" ) ) as "Daily Incremental Budget (Ideal, Adv Currency)"
    from
        cte0
        left join provisioning2.AdGroup ag
            on cte0."Ad Group ID" = ag.AdGroupId
        left join provisioning2.Advertiser adv
            on cte0."Advertiser ID" = adv.AdvertiserId
        left join provisioning2.Campaign camp
            on cte0."Campaign ID" = camp.CampaignId
        left join provisioning2.CampaignFlight cf
            on cte0."Campaign ID" = cf.CampaignID
            and cte0."Campaign Flight ID" = cf.CampaignFlightID
    group by
        adv.AdvertiserName,
        cte0."Advertiser ID",
        adv.CurrencyCodeId,
        camp.CampaignName,
        cte0."Campaign ID",
        ag.AdGroupName,
        cte0."Ad Group ID",
        cte0."Ad Group Decision Power",
        cte0."Campaign Flight ID",
        datediff('day', current_date, cf.EndDateExclusiveUTC::date),
        cf.BudgetInAdvertiserCurrency,
        cf.EndDateExclusiveUTC
),
cteRowCount as (
    select *, count(*) over () as RowCount from cteF
)
select /*+ label('v2;3;7520868;4493688;74717982;148945185;0;1;4;8;00;101;101;10;1;0') */
    cteRowCount."Advertiser",
    cteRowCount."Advertiser ID",
    cteRowCount."Advertiser Currency Code",
    cteRowCount."Campaign",
    cteRowCount."Campaign ID",
    cteRowCount."Ad Group",
    cteRowCount."Ad Group ID",
    cteRowCount."Ad Group Decision Power",
    cteRowCount."Campaign Flight ID",
    cteRowCount."Days Remaining in Flight",
    cteRowCount."Campaign Flight Budget (Adv Currency)",
    cteRowCount."Campaign Flight End Date UTC Exclusive",
    cteRowCount."Ad Group Forecasted Spend (Adv Currency)",
    cteRowCount."Daily Incremental Budget (Constrained, Adv Currency)",
    cteRowCount."Daily Incremental Budget (Fair, Adv Currency)",
    cteRowCount."Daily Incremental Budget (Ideal, Adv Currency)"
from cteRowCount
where case when RowCount > 1000000 then ( 'TTD-TMR: Too many rows: ' || RowCount::varchar(100) || '/' || 1000000 )::int else 1 end = 1
order by
    cteRowCount."Advertiser",
    cteRowCount."Advertiser ID",
    cteRowCount."Advertiser Currency Code",
    cteRowCount."Campaign",
    cteRowCount."Campaign ID",
    cteRowCount."Ad Group",
    cteRowCount."Ad Group ID",
    cteRowCount."Ad Group Decision Power",
    cteRowCount."Campaign Flight ID",
    cteRowCount."Days Remaining in Flight",
    cteRowCount."Campaign Flight Budget (Adv Currency)",
    cteRowCount."Campaign Flight End Date UTC Exclusive";



-- Query for ResultSet 7520869 (Ad Group View)

with pte_IBR as (


select
    agf.SnapshotDate
    ,agf.PartnerId
    ,agf.AdvertiserId
    ,agf.CampaignId
    ,agf.CampaignFlightId
    ,agf.AdGroupId
    ,agf.ForecastedSpend
    ,agf.DecisionPower
    ,agf.DailyIncrementalBudgetIdeal
    ,agf.DailyIncrementalBudgetFair
    ,agf.DailyIncrementalBudgetConstrained
    ,agf.ForecastedImpressions
    ,agf.DailyIncrementalImpressionsIdeal
    ,agf.DailyIncrementalImpressionsFair
    ,agf.DailyIncrementalImpressionsConstrained
from reports.AdGroupForecasts agf
inner join provisioning2.CampaignFlight cf on cf.CampaignId = agf.CampaignId and cf.CampaignFlightId = agf.CampaignFlightId
where
    (agf.AdvertiserId in ('8gwz9hf'))
    and agf.SnapshotDate = current_date
    and cf.IsCurrent = 1


), cte0 as (

    select

        pte_IBR.AdvertiserId as "Advertiser ID",

        pte_IBR.CampaignId as "Campaign ID",

        pte_IBR.AdGroupId as "Ad Group ID",

        pte_IBR.DecisionPower as "Ad Group Decision Power",

        pte_IBR.CampaignFlightId as "Campaign Flight ID",

        zeroifnull( sum( pte_IBR.ForecastedSpend ) ) as "Ad Group Forecasted Spend (Adv Currency)",

        zeroifnull( sum( pte_IBR.DailyIncrementalBudgetConstrained ) ) as "Daily Incremental Budget (Constrained, Adv Currency)",

        zeroifnull( sum( pte_IBR.DailyIncrementalBudgetFair ) ) as "Daily Incremental Budget (Fair, Adv Currency)",

        zeroifnull( sum( pte_IBR.DailyIncrementalBudgetIdeal ) ) as "Daily Incremental Budget (Ideal, Adv Currency)"

    from

        pte_IBR

    where

        (pte_IBR.AdvertiserId in ('8gwz9hf'))

    group by

        pte_IBR.AdvertiserId,

        pte_IBR.CampaignId,

        pte_IBR.AdGroupId,

        pte_IBR.DecisionPower,

        pte_IBR.CampaignFlightId

),

cteF as (

    select

        adv.AdvertiserName as Advertiser,

        cte0."Advertiser ID" as "Advertiser ID",

        adv.CurrencyCodeId as "Advertiser Currency Code",

        camp.CampaignName as Campaign,

        cte0."Campaign ID" as "Campaign ID",

        ag.AdGroupName as "Ad Group",

        cte0."Ad Group ID" as "Ad Group ID",

        cte0."Ad Group Decision Power" as "Ad Group Decision Power",

        cte0."Campaign Flight ID" as "Campaign Flight ID",

        datediff('day', current_date, cf.EndDateExclusiveUTC::date) as "Days Remaining in Flight",

        cf.BudgetInAdvertiserCurrency as "Campaign Flight Budget (Adv Currency)",

        cf.EndDateExclusiveUTC as "Campaign Flight End Date UTC Exclusive",

        zeroifnull( sum( cte0."Ad Group Forecasted Spend (Adv Currency)" ) ) as "Ad Group Forecasted Spend (Adv Currency)",

        zeroifnull( sum( cte0."Daily Incremental Budget (Constrained, Adv Currency)" ) ) as "Daily Incremental Budget (Constrained, Adv Currency)",

        zeroifnull( sum( cte0."Daily Incremental Budget (Fair, Adv Currency)" ) ) as "Daily Incremental Budget (Fair, Adv Currency)",

        zeroifnull( sum( cte0."Daily Incremental Budget (Ideal, Adv Currency)" ) ) as "Daily Incremental Budget (Ideal, Adv Currency)"

    from

        cte0

        left join provisioning2.AdGroup ag

            on cte0."Ad Group ID" = ag.AdGroupId

        left join provisioning2.Advertiser adv

            on cte0."Advertiser ID" = adv.AdvertiserId

        left join provisioning2.Campaign camp

            on cte0."Campaign ID" = camp.CampaignId

        left join provisioning2.CampaignFlight cf

            on cte0."Campaign ID" = cf.CampaignID

            and cte0."Campaign Flight ID" = cf.CampaignFlightID

    group by

        adv.AdvertiserName,

        cte0."Advertiser ID",

        adv.CurrencyCodeId,

        camp.CampaignName,

        cte0."Campaign ID",

        ag.AdGroupName,

        cte0."Ad Group ID",

        cte0."Ad Group Decision Power",

        cte0."Campaign Flight ID",

        datediff('day', current_date, cf.EndDateExclusiveUTC::date),

        cf.BudgetInAdvertiserCurrency,

        cf.EndDateExclusiveUTC

),

cteRowCount as (

    select *, count(*) over () as RowCount from cteF

)

select /*+ label('v2;3;7520869;4493688;74717982;148945185;0;1;4;8;00;101;101;10;1;0') */

    cteRowCount."Advertiser",

    cteRowCount."Advertiser ID",

    cteRowCount."Advertiser Currency Code",

    cteRowCount."Campaign",

    cteRowCount."Campaign ID",

    cteRowCount."Ad Group",

    cteRowCount."Ad Group ID",

    cteRowCount."Ad Group Decision Power",

    cteRowCount."Campaign Flight ID",

    cteRowCount."Days Remaining in Flight",

    cteRowCount."Campaign Flight Budget (Adv Currency)",

    cteRowCount."Campaign Flight End Date UTC Exclusive",

    cteRowCount."Ad Group Forecasted Spend (Adv Currency)",

    cteRowCount."Daily Incremental Budget (Constrained, Adv Currency)",

    cteRowCount."Daily Incremental Budget (Fair, Adv Currency)",

    cteRowCount."Daily Incremental Budget (Ideal, Adv Currency)"

from cteRowCount

where case when RowCount > 1000000 then ( 'TTD-TMR: Too many rows: ' || RowCount::varchar(100) || '/' || 1000000 )::int else 1 end = 1

order by

    cteRowCount."Advertiser",

    cteRowCount."Advertiser ID",

    cteRowCount."Advertiser Currency Code",

    cteRowCount."Campaign",

    cteRowCount."Campaign ID",

    cteRowCount."Ad Group",

    cteRowCount."Ad Group ID",

    cteRowCount."Ad Group Decision Power",

    cteRowCount."Campaign Flight ID",

    cteRowCount."Days Remaining in Flight",

    cteRowCount."Campaign Flight Budget (Adv Currency)",

    cteRowCount."Campaign Flight End Date UTC Exclusive";


select distinct
    *
From reports.RTBPlatformReport
where AdvertiserId = '8gwz9hf'
and ReportHourUtc > '2025-07-12'


SELECT
                    DATE(rtb.ReportHourUtc::timestamptz AT TIME ZONE 'JST') as jst_date
                    ,rtb.PartnerId
					,rtb.AdvertiserId
                    ,adv.AdvertiserName
					,rtb.CampaignId
                    ,cp.CampaignName
					,rtb.AdGroupId
                    ,adg.AdGroupName
 					,rtb.CreativeId
                    ,cr.Name AS CreativeName
					,rtb.DeviceType
 					,rtb.DealId
 					,rtb.PrivateContractId
                    ,pc.Name as DealName
 					,rtb.SupplyVendorPublisherId
					,zeroifnull( SUM( rtb.BidCount ) ) as BidCount
					,zeroifnull( SUM( rtb.ImpressionCount ) ) as ImpressionCount
					,zeroifnull( SUM( rtb.CustomCPACount ) ) as CustomConversions
                    ,zeroifnull( SUM( rtb.VideoEventFirstQuarterCount ) ) as "Player 25% Complete"
                    ,zeroifnull( sum( rtb.VideoEventMidPointCount ) ) as "Player 50% Complete"
                    ,zeroifnull( sum( rtb.VideoEventThirdQuarterCount ) ) as "Player 75% Complete"
                    ,zeroifnull( sum( rtb.VideoEventCompleteCount ) ) as "Player Completed Views"
					,zeroifnull( sum( rtb.TTDCostInAdvertiserCurrency ) ) as TTDCost
                    ,zeroifnull( sum( rtb.PartnerCostInAdvertiserCurrency ) ) as PartnerCost
					,zeroifnull( sum( rtb.AdvertiserCostInAdvertiserCurrency ) ) as AdvertiserCost
					,zeroifnull( sum( rtb.DataCostInAdvertiserCurrency ) ) as DataCost
                    ,zeroifnull( SUM( LastView1Count ) ) as LastView1Count
                    ,zeroifnull( SUM( LastView2Count ) ) as LastView2Count
				FROM
                    reports.RTBPlatformReport rtb
				    LEFT OUTER JOIN provisioning2.Advertiser adv
				        ON rtb.AdvertiserId = adv.AdvertiserId
                    LEFT OUTER JOIN provisioning2.Campaign cp
				        ON rtb.CampaignId = cp.CampaignId
                    LEFT OUTER JOIN provisioning2.AdGroup adg
                        ON rtb.AdGroupId = adg.AdGroupId
                    LEFT OUTER JOIN provisioning2.Creative cr
				        ON rtb.CreativeId = cr.CreativeId
				    LEFT OUTER JOIN provisioning2.PrivateContract pc
				        ON rtb.PrivateContractId = pc.PrivateContractId
                WHERE 1=1
                    AND (
                            (ReportHourUtc >= ('2025-06-01'::timestamp at timezone 'Asia/Tokyo')::timestamp)
                            AND
                            (ReportHourUtc < ('2025-07-17'::timestamp at timezone 'Asia/Tokyo')::timestamp)
                        )
                    AND rtb.AdvertiserId IN ('wki13r7')
                    --AND rtb.CampaignId IN ('{CampaignIds}')
				GROUP BY
				    DATE(rtb.ReportHourUtc::timestamptz AT TIME ZONE 'JST')
                    ,rtb.PartnerId
					,rtb.AdvertiserId
                    ,adv.AdvertiserName
					,rtb.CampaignId
                    ,cp.CampaignName
					,rtb.AdGroupId
                    ,adg.AdGroupName
 					,rtb.CreativeId
                    ,cr.Name
					,rtb.DeviceType
 					,rtb.DealId
 					,rtb.PrivateContractId
                    ,pc.Name
 					,rtb.SupplyVendorPublisherId
				    ,rtb.Region