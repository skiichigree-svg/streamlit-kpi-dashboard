WITH
    RTBdata AS (
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
                            (ReportHourUtc >= ('{StartDate}'::timestamp at timezone 'Asia/Tokyo')::timestamp)
                            AND
                            (ReportHourUtc < ('{EndDate}'::timestamp at timezone 'Asia/Tokyo')::timestamp)
                        )
                    AND rtb.AdvertiserId IN ({AdvertiserId})
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
    ),

    labeled AS (
                SELECT
                    jst_date
                    ,EXTRACT(WEEK FROM DATE_TRUNC('week', jst_date) + INTERVAL '1 day') - EXTRACT(WEEK FROM DATE_TRUNC('month', jst_date) + INTERVAL '1 day') + 1 AS 'WeekOfMonth'
                    ,CASE DAYOFWEEK(jst_date)
                        WHEN 1 THEN '日'
                        WHEN 2 THEN '月'
                        WHEN 3 THEN '火'
                        WHEN 4 THEN '水'
                        WHEN 5 THEN '木'
                        WHEN 6 THEN '金'
                        WHEN 7 THEN '土'
                    END as 'DayOfWeek'
                    ,PartnerId
					,AdvertiserId
                    ,AdvertiserName
					,CampaignId
                    ,CampaignName
					,AdGroupId
                    ,AdGroupName
                    ,CASE
                        WHEN AdGroupName LIKE 'TVer PMP\_%' ESCAPE '\' THEN 'TVer'
                        WHEN AdGroupName LIKE 'AJA\_%' ESCAPE '\' THEN 'AJA'
                        ELSE 'Unknown'
                    END AS SSP
                    ,CASE
                        WHEN AdGroupName LIKE 'AJA\_IDレス\_%' ESCAPE '\' THEN 'IDレス'
                        ELSE 'IDあり'
                    END AS IsId
                    ,CASE
                        WHEN AdGroupName LIKE 'TVer PMP\_All\_%' ESCAPE '\' THEN 'All'
                        WHEN AdGroupName LIKE '%\_IDあり\_女性\_%' ESCAPE '\' THEN 'IDあり-女性'
                        WHEN AdGroupName LIKE '%\_IDレス\_女性\_%' ESCAPE '\' THEN 'IDレス-女性'
                        WHEN AdGroupName LIKE '%\_IDあり\_男性\_%' ESCAPE '\' THEN 'IDあり-男性'
                        WHEN AdGroupName LIKE '%\_IDレス\_男性\_%' ESCAPE '\' THEN 'IDレス-男性'
                        WHEN AdGroupName LIKE '%\_Koa\_%' ESCAPE '\' THEN 'Koa'
                        WHEN AdGroupName LIKE '%\_IDあり\_ドラマ\_%' ESCAPE '\' THEN 'IDあり-ドラマ'
                        WHEN AdGroupName LIKE '%\_IDレス\_ドラマ\_%' ESCAPE '\' THEN 'IDレス-ドラマ'
                        WHEN AdGroupName LIKE '%\_ドラマ\_%' ESCAPE '\' THEN 'IDあり-ドラマ'
                        WHEN AdGroupName LIKE '%\_IDあり\_バラエティ\_%' ESCAPE '\' THEN 'IDあり-バラエティ'
                        WHEN AdGroupName LIKE '%\_IDレス\_バラエティ\_%' ESCAPE '\' THEN 'IDレス-バラエティ'
                        WHEN AdGroupName LIKE '%\_バラエティ\_%' ESCAPE '\' THEN 'IDあり-バラエティ'
                        WHEN AdGroupName LIKE '%\_Comic\_%' ESCAPE '\' THEN 'マンガ'
                        WHEN AdGroupName LIKE '%\_Game\_%' ESCAPE '\' THEN 'ゲーム'
                        WHEN AdGroupName LIKE '%\_Automotive\_%' ESCAPE '\' THEN '車'
                        WHEN AdGroupName LIKE '%\_iOSユーザー世帯\_%' ESCAPE '\' THEN 'iOSユーザー世帯'
                        WHEN AdGroupName LIKE '%\_GameComic\_%' ESCAPE '\' THEN 'ゲーム・マンガ'
                        WHEN AdGroupName LIKE '%\_RTG\_%' ESCAPE '\' THEN 'RTG'
                        ELSE 'Undefined'
                    END AS Target
 					,CreativeId
                    ,CreativeName
                    ,CASE
                        WHEN CreativeName LIKE '%\_omotomeitadaita\_%' ESCAPE '\' THEN 'お求め頂いた～_CR1_2503'
                        WHEN CreativeName LIKE '%\_oreraguna\_%' ESCAPE '\' THEN '俺だけレベルアップな件_CR2_2503'
                        WHEN CreativeName LIKE '%\_access-SAIKYO\_%' ESCAPE '\' THEN 'アクセス_CR3'
                        WHEN CreativeName LIKE '%\_Boukunheika-no-akuzyo\_%' ESCAPE '\' THEN '暴君陛下の悪女です_CR1_2504'
                        WHEN CreativeName LIKE '%\_saikyono\_%' ESCAPE '\' THEN '最強の王様_' || SUBSTRING(CreativeName FROM POSITION('_CR' IN CreativeName) FOR 4) || '_' || SUBSTRING(CreativeName FROM 1 FOR 4)
                        WHEN CreativeName LIKE '%\_reimei\_%' ESCAPE '\' THEN 'まだ、黎明なだけ_' || SUBSTRING(CreativeName FROM POSITION('_CR' IN CreativeName) FOR 4) || '_' || SUBSTRING(CreativeName FROM 1 FOR 4)
                        WHEN CreativeName LIKE '%\_toshishita_\_%' ESCAPE '\' THEN '年下夫の未来のために_' || SUBSTRING(CreativeName FROM POSITION('_CR' IN CreativeName) FOR 4) || '_' || SUBSTRING(CreativeName FROM 1 FOR 4)
                        ELSE CreativeName
                    END AS Creative
					,DeviceType
 					,DealId
 					,PrivateContractId
                    ,DealName
 					,SupplyVendorPublisherId
                    ,CASE
                        WHEN SupplyVendorPublisherId = 817 THEN '日本テレビ'
                        WHEN SupplyVendorPublisherId = 2269 THEN '日本テレビ'
                        WHEN SupplyVendorPublisherId = 823 THEN 'テレビ朝日'
                        WHEN SupplyVendorPublisherId = 2270 THEN 'テレビ朝日'
                        WHEN SupplyVendorPublisherId = 824 THEN 'TBS'
                        WHEN SupplyVendorPublisherId = 2268 THEN 'TBS'
                        WHEN SupplyVendorPublisherId = 825 THEN 'テレビ東京'
                        WHEN SupplyVendorPublisherId = 2267 THEN 'テレビ東京'
                        WHEN SupplyVendorPublisherId = 826 THEN 'フジテレビ'
                        WHEN SupplyVendorPublisherId = 2326 THEN 'テレビ朝日'
                        WHEN SupplyVendorPublisherId = 1184 THEN '毎日放送'
                        WHEN SupplyVendorPublisherId = 2340 THEN '毎日放送'
                        WHEN SupplyVendorPublisherId = 1185 THEN '朝日放送'
                        WHEN SupplyVendorPublisherId = 2341 THEN '朝日放送'
                        WHEN SupplyVendorPublisherId = 1186 THEN '関西テレビ'
                        WHEN SupplyVendorPublisherId = 2319 THEN '関西テレビ'
                        WHEN SupplyVendorPublisherId = 1187 THEN '読売テレビ'
                        WHEN SupplyVendorPublisherId = 2323 THEN '読売テレビ'
                        WHEN SupplyVendorPublisherId = 1302 THEN 'テレビ大阪'
                        WHEN SupplyVendorPublisherId = 2353 THEN 'テレビ大阪'
                        ELSE 'Unknown'
                    END AS 放送局
                    ,CASE
                        WHEN AdGroupName LIKE 'TVer PMP\_All\_%' ESCAPE '\' THEN 'All'
                        WHEN AdGroupName LIKE '%\_女性\_%' ESCAPE '\' THEN 'All'
                        WHEN AdGroupName LIKE '%\_男性\_%' ESCAPE '\' THEN 'All'
                        WHEN AdGroupName LIKE '%\_Koa\_%' ESCAPE '\' THEN 'Koa'
                        WHEN AdGroupName LIKE '%\_Comic\_%' ESCAPE '\' THEN 'マンガ関心'
                        WHEN AdGroupName LIKE '%\_Game\_%' ESCAPE '\' THEN 'ゲーム関心'
                        WHEN AdGroupName LIKE '%\_Automotive\_%' ESCAPE '\' THEN '車関心'
                        WHEN AdGroupName LIKE '%\_iOSユーザー世帯\_%' ESCAPE '\' THEN 'iOSユーザー世帯'
                        WHEN AdGroupName LIKE '%\_ドラマ\_%' ESCAPE '\' THEN
                            CASE SupplyVendorPublisherId
                                WHEN 1186 THEN 'KTV_ドラマ'
                                WHEN 2267 THEN 'TX_ドラマ'
                                WHEN 2268 THEN 'TBS_ドラマ'
                                WHEN 2270 THEN 'EX_ドラマ'
                                WHEN 2323 THEN 'YTV_ドラマ'
                                WHEN 2340 THEN 'MBS_ドラマ'
                                WHEN 2341 THEN 'ABC_ドラマ'
                                WHEN 2353 THEN 'TVO_ドラマ'
                                WHEN 817 THEN 'NTV_ドラマ'
                                WHEN 826 THEN 'CX_ドラマ'
                                WHEN 2269 THEN 'NTV_ドラマ'
                                WHEN 2326 THEN 'EX_ドラマ'
                                WHEN 2319 THEN 'KTV_ドラマ'
                            END
                        WHEN AdGroupName LIKE '%\_バラエティ\_%' ESCAPE '\' THEN
                            CASE SupplyVendorPublisherId
                                WHEN 1186 THEN 'KTV_バラエティ'
                                WHEN 2267 THEN 'TX_バラエティ'
                                WHEN 2268 THEN 'TBS_バラエティ'
                                WHEN 2270 THEN 'EX_バラエティ'
                                WHEN 2323 THEN 'YTV_バラエティ'
                                WHEN 2340 THEN 'MBS_バラエティ'
                                WHEN 2341 THEN 'ABC_バラエティ'
                                WHEN 2353 THEN 'TVO_バラエティ'
                                WHEN 817 THEN 'NTV_バラエティ'
                                WHEN 826 THEN 'CX_バラエティ'
                                WHEN 2269 THEN 'NTV_バラエティ'
                                WHEN 2326 THEN 'EX_バラエティ'
                                WHEN 2319 THEN 'KTV_バラエティ'
                            END
                        ELSE 'Undefined'
                    END AS 放送局別ターゲティング
					,BidCount
					,ImpressionCount
					,CustomConversions
                    ,"Player 25% Complete"
                    ,"Player 50% Complete"
                    ,"Player 75% Complete"
                    ,"Player Completed Views"
					,TTDCost
                    ,PartnerCost
					,AdvertiserCost
					,DataCost
                    ,LastView1Count
                    ,LastView2Count
				FROM
                    RTBdata
)

SELECT
    jst_date
    ,WeekOfMonth
    ,DayOfWeek
    ,PartnerId
    ,AdvertiserId
    ,AdvertiserName
    ,CampaignId
    ,CampaignName
    ,AdGroupId
    ,AdGroupName
    ,SSP
    ,IsId
    ,Target
    ,CreativeId
    ,CreativeName
    ,Creative
    ,DeviceType
    ,DealId
    ,PrivateContractId
    ,DealName
    ,SupplyVendorPublisherId
    ,放送局
    ,放送局別ターゲティング
    ,BidCount
    ,ImpressionCount
    ,CustomConversions
    ,"Player 25% Complete"
    ,"Player 50% Complete"
    ,"Player 75% Complete"
    ,"Player Completed Views"
    ,TTDCost
    ,PartnerCost
    ,AdvertiserCost
    ,DataCost
    ,LastView1Count
    ,LastView2Count
FROM
    labeled
ORDER BY
    jst_date
    ,CampaignName
    ,AdGroupName
    ,CreativeName;


