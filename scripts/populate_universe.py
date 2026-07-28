#!/usr/bin/env python3
"""
IndiaPulse
Milestone 2.1 - Market Universe Generator
"""

from pathlib import Path
import csv

# ---------------------------------------------------------------------
# Project Paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_DIR = PROJECT_ROOT / "data" / "universe"

UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# CSV Writer
# ---------------------------------------------------------------------

def write_csv(filename, header, rows):
    filepath = UNIVERSE_DIR / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Created {filename} ({len(rows)} rows)")


HEADER = [
    "Symbol",
    "Name",
    "Category",
    "Exchange",
    "Provider",
    "AssetClass",
    "Frequency",
    "Priority",
    "Active",
    "Remarks"
]
# ---------------------------------------------------------------------
# Broad Market Universe
# ---------------------------------------------------------------------

broad_market = [

["NIFTY50","Nifty 50","Broad Market","NSE","NSE","Equity","Daily",1,True,"Benchmark"],

["NIFTYNEXT50","Nifty Next 50","Broad Market","NSE","NSE","Equity","Daily",2,True,""],

["NIFTY100","Nifty 100","Broad Market","NSE","NSE","Equity","Daily",3,True,""],

["NIFTY200","Nifty 200","Broad Market","NSE","NSE","Equity","Daily",4,True,""],

["NIFTY500","Nifty 500","Broad Market","NSE","NSE","Equity","Daily",5,True,""],


["NIFTYTOTALMARKET","Nifty Total Market","Broad Market","NSE","NSE","Equity","Daily",7,True,""],

["NIFTYMIDCAP50","Nifty Midcap 50","Broad Market","NSE","NSE","Equity","Daily",8,True,""],

["NIFTYMIDCAP100","Nifty Midcap 100","Broad Market","NSE","NSE","Equity","Daily",9,True,""],

["NIFTYMIDCAP150","Nifty Midcap 150","Broad Market","NSE","NSE","Equity","Daily",10,True,""],

["NIFTYSMALLCAP50","Nifty Smallcap 50","Broad Market","NSE","NSE","Equity","Daily",11,True,""],


["NIFTYSMALLCAP250","Nifty Smallcap 250","Broad Market","NSE","NSE","Equity","Daily",13,True,""],



]

sectors = [
    ["NIFTYAUTO","Nifty Auto","Sector","NSE","NSE","Equity","Daily",1,True,""],
    ["NIFTYBANK","Nifty Bank","Sector","NSE","NSE","Equity","Daily",2,True,""],
    ["NIFTYFINSERVICE","Nifty Financial Services","Sector","NSE","NSE","Equity","Daily",3,True,""],
    ["NIFTYFMCG","Nifty FMCG","Sector","NSE","NSE","Equity","Daily",4,True,""],
    ["NIFTYHEALTHCARE","Nifty Healthcare","Sector","NSE","NSE","Equity","Daily",5,True,""],
    ["NIFTYIT","Nifty IT","Sector","NSE","NSE","Equity","Daily",6,True,""],
    ["NIFTYMEDIA","Nifty Media","Sector","NSE","NSE","Equity","Daily",7,True,""],
    ["NIFTYMETAL","Nifty Metal","Sector","NSE","NSE","Equity","Daily",8,True,""],
    ["NIFTYPHARMA","Nifty Pharma","Sector","NSE","NSE","Equity","Daily",9,True,""],
    ["NIFTYPSUBANK","Nifty PSU Bank","Sector","NSE","NSE","Equity","Daily",10,True,""],
    ["NIFTYPRIVATEBANK","Nifty Private Bank","Sector","NSE","NSE","Equity","Daily",11,True,""],
    ["NIFTYREALTY","Nifty Realty","Sector","NSE","NSE","Equity","Daily",12,True,""],
    ["NIFTYCONSUMERDURABLES","Nifty Consumer Durables","Sector","NSE","NSE","Equity","Daily",13,True,""],
    ["NIFTYENERGY","Nifty Energy","Sector","NSE","NSE","Equity","Daily",15,True,""],
    ["NIFTYINFRA","Nifty Infrastructure","Sector","NSE","NSE","Equity","Daily",16,True,""],
    ["NIFTYCOMMODITIES","Nifty Commodities","Sector","NSE","NSE","Equity","Daily",17,True,""],
    ["NIFTYSERVICES","Nifty Services","Sector","NSE","NSE","Equity","Daily",18,True,""],
    ["NIFTYCONSUMPTION","Nifty India Consumption","Sector","NSE","NSE","Equity","Daily",19,True,""],
    ["NIFTYPSE","Nifty PSE","Sector","NSE","NSE","Equity","Daily",20,True,""]
]


# ---------------------------------------------------------------------
# Industry Universe
# ---------------------------------------------------------------------

industries = [

["NIFTYCHEMICAL","Nifty Chemicals","Industry","NSE","NSE","Equity","Daily",1,True,""],
["NIFTYCAPITALMARKET","Nifty Capital Markets","Industry","NSE","NSE","Equity","Daily",2,True,""],
["NIFTYTELECOM","Nifty Telecom","Industry","NSE","NSE","Equity","Daily",3,True,""],
["NIFTYLOGISTICS","Nifty Logistics","Industry","NSE","NSE","Equity","Daily",4,True,""],
["NIFTYAVIATION","Nifty Aviation","Industry","NSE","NSE","Equity","Daily",5,True,""],
["NIFTYCEMENT","Nifty Cement","Industry","NSE","NSE","Equity","Daily",6,True,""],
["NIFTYCONSTRUCTION","Nifty Construction","Industry","NSE","NSE","Equity","Daily",7,True,""],
["NIFTYDEFENCE","Nifty Defence","Industry","NSE","NSE","Equity","Daily",8,True,""],
["NIFTYRETAIL","Nifty Retail","Industry","NSE","NSE","Equity","Daily",9,True,""],
["NIFTYTEXTILE","Nifty Textile","Industry","NSE","NSE","Equity","Daily",10,True,""],
["NIFTYSUGAR","Nifty Sugar","Industry","NSE","NSE","Equity","Daily",11,True,""],
["NIFTYFERTILIZER","Nifty Fertilizer","Industry","NSE","NSE","Equity","Daily",12,True,""],
["NIFTYAUTOCOMP","Nifty Auto Components","Industry","NSE","NSE","Equity","Daily",13,True,""],
["NIFTYPOWER","Nifty Power","Industry","NSE","NSE","Equity","Daily",14,True,""],
["NIFTYHOSPITAL","Nifty Hospitals","Industry","NSE","NSE","Equity","Daily",15,True,""],
["NIFTYINSURANCE","Nifty Insurance","Industry","NSE","NSE","Equity","Daily",16,True,""],
["NIFTYNBFC","Nifty NBFC","Industry","NSE","NSE","Equity","Daily",17,True,""],
["NIFTYINTERNET","Nifty Internet","Industry","NSE","NSE","Equity","Daily",18,True,""],
["NIFTYRENEWABLE","Nifty Renewable Energy","Industry","NSE","NSE","Equity","Daily",19,True,""],
["NIFTYCABLE","Nifty Cables","Industry","NSE","NSE","Equity","Daily",20,True,""],
["NIFTYELECTRICAL","Nifty Electrical Equipment","Industry","NSE","NSE","Equity","Daily",21,True,""],
["NIFTYPACKAGING","Nifty Packaging","Industry","NSE","NSE","Equity","Daily",22,True,""],
["NIFTYENGINEERING","Nifty Engineering","Industry","NSE","NSE","Equity","Daily",23,True,""],
["NIFTYHOTELS","Nifty Hotels","Industry","NSE","NSE","Equity","Daily",24,True,""],
["NIFTYSHIPPING","Nifty Shipping","Industry","NSE","NSE","Equity","Daily",25,True,""]

]


# ---------------------------------------------------------------------
# Theme Universe
# ---------------------------------------------------------------------

themes = [

["MANUFACTURING","India Manufacturing","Theme","NSE","NSE","Equity","Daily",1,True,""],
["DEFENCE","Defence","Theme","NSE","NSE","Equity","Daily",2,True,""],
["EV","Electric Vehicles","Theme","NSE","NSE","Equity","Daily",3,True,""],
["DIGITAL","Digital India","Theme","NSE","NSE","Equity","Daily",4,True,""],
["CPSE","CPSE","Theme","NSE","NSE","Equity","Daily",5,True,""],
["PSU","Public Sector","Theme","NSE","NSE","Equity","Daily",6,True,""],
["RURAL","Rural India","Theme","NSE","NSE","Equity","Daily",7,True,""],
["HOUSING","Housing","Theme","NSE","NSE","Equity","Daily",8,True,""],
["TOURISM","Tourism","Theme","NSE","NSE","Equity","Daily",9,True,""],
["ESG","ESG","Theme","NSE","NSE","Equity","Daily",10,True,""],
["INFRA","Infrastructure","Theme","NSE","NSE","Equity","Daily",11,True,""],
["MNC","MNC","Theme","NSE","NSE","Equity","Daily",12,True,""],
["CONSUMPTION","Consumption","Theme","NSE","NSE","Equity","Daily",13,True,""],
["MOBILITY","Mobility","Theme","NSE","NSE","Equity","Daily",14,True,""],
["DIVIDEND","Dividend Opportunities","Theme","NSE","NSE","Equity","Daily",15,True,""],
["AGRICULTURE","Agriculture","Theme","NSE","NSE","Equity","Daily",16,True,""],
["EMS","Electronics Manufacturing Services","Theme","NSE","NSE","Equity","Daily",17,True,""],
["RAILWAYS","Railways","Theme","NSE","NSE","Equity","Daily",18,True,""],
["BATTERY","Battery & Energy Storage","Theme","NSE","NSE","Equity","Daily",19,True,""],
["SEMICONDUCTOR","Semiconductor","Theme","NSE","NSE","Equity","Daily",20,True,""],
["DATACENTER","Data Centers & Digital Infra","Theme","NSE","NSE","Equity","Daily",21,True,""],
["WATER","Water","Theme","NSE","NSE","Equity","Daily",22,True,""],
["SPECIALTYCHEM","Specialty Chemicals","Theme","NSE","NSE","Equity","Daily",23,True,""],
["CAPEXINDUSTRIALS","Capex & Industrials","Theme","NSE","NSE","Equity","Daily",24,True,""]

]


# ---------------------------------------------------------------------
# Factor Universe
# ---------------------------------------------------------------------

factors = [

["ALPHA50","Alpha 50","Factor","NSE","NSE","Equity","Daily",1,True,""],
["QUALITY30","Quality 30","Factor","NSE","NSE","Equity","Daily",2,True,""],
["VALUE20","Value 20","Factor","NSE","NSE","Equity","Daily",3,True,""],
["MOMENTUM30","Momentum 30","Factor","NSE","NSE","Equity","Daily",4,True,""],
["LOWVOL30","Low Volatility 30","Factor","NSE","NSE","Equity","Daily",5,True,""],
["LOWBETA","Low Beta","Factor","NSE","NSE","Equity","Daily",7,True,""],
["EQUALWEIGHT","Equal Weight","Factor","NSE","NSE","Equity","Daily",8,True,""],
["DIVIDEND50","Dividend Opportunities 50","Factor","NSE","NSE","Equity","Daily",9,True,""],
["GROWTH","Growth","Factor","NSE","NSE","Equity","Daily",10,True,""]

]


fixed_income = [

["GSEC10Y","10 Year G-Sec","Fixed Income","NSE","NSE","Bond","Daily",1,True,""],
["GSEC813","8-13 Year G-Sec","Fixed Income","NSE","NSE","Bond","Daily",2,True,""],
["SDL","State Development Loan","Fixed Income","NSE","NSE","Bond","Daily",3,True,""],
["BHARATBOND2030","Bharat Bond 2030","Fixed Income","NSE","NSE","Bond","Daily",4,True,""],
["BHARATBOND2031","Bharat Bond 2031","Fixed Income","NSE","NSE","Bond","Daily",5,True,""],
["CORPBOND","Corporate Bond","Fixed Income","NSE","NSE","Bond","Daily",6,True,""],
["LIQUID","Liquid Index","Fixed Income","NSE","NSE","Bond","Daily",7,True,""],
["MONEYMARKET","Money Market","Fixed Income","NSE","NSE","Bond","Daily",8,True,""]

]


commodities = [

["GOLD","Gold","Commodity","MCX","MCX","Commodity","Daily",1,True,""],
["SILVER","Silver","Commodity","MCX","MCX","Commodity","Daily",2,True,""],
["COPPER","Copper","Commodity","MCX","MCX","Commodity","Daily",3,True,""],
["ALUMINIUM","Aluminium","Commodity","MCX","MCX","Commodity","Daily",4,True,""],
["ZINC","Zinc","Commodity","MCX","MCX","Commodity","Daily",5,True,""],
["NICKEL","Nickel","Commodity","MCX","MCX","Commodity","Daily",6,True,""],
["LEAD","Lead","Commodity","MCX","MCX","Commodity","Daily",7,True,""],
["BRENT","Brent Crude","Commodity","ICE","ICE","Commodity","Daily",8,True,""],
["WTI","WTI Crude","Commodity","NYMEX","NYMEX","Commodity","Daily",9,True,""],
["NATGAS","Natural Gas","Commodity","MCX","MCX","Commodity","Daily",10,True,""],
["COAL","Coal","Commodity","Global","Various","Commodity","Daily",11,True,""],
["STEEL","Steel","Commodity","Global","Various","Commodity","Daily",12,True,""]

]


MACRO_HEADER = [
    "Symbol",
    "Name",
    "Category",
    "Provider",
    "Frequency",
    "Unit",
    "Source",
    "Priority",
    "Active",
    "Remarks"
]
macro = [

["CPI","Consumer Price Index","Inflation","MOSPI","Monthly","%","MOSPI",1,True,""],
["WPI","Wholesale Price Index","Inflation","Commerce","Monthly","%","GoI",2,True,""],
["REPO_RATE","Repo Rate","Monetary","RBI","Event","%","RBI",3,True,""],
["CRR","Cash Reserve Ratio","Monetary","RBI","Event","%","RBI",4,True,""],
["FOREX","Forex Reserves","External","RBI","Weekly","USD Bn","RBI",5,True,""],
["USDINR","USD/INR","FX","RBI","Daily","Rate","RBI",6,True,""],
["GST","GST Collection","Fiscal","GSTN","Monthly","₹ Cr","GSTN",7,True,""],
["GDP","GDP Growth","Growth","MOSPI","Quarterly","%","MOSPI",8,True,""],
["PMI_MFG","PMI Manufacturing","Growth","S&P","Monthly","Index","S&P",9,True,""],
["PMI_SERV","PMI Services","Growth","S&P","Monthly","Index","S&P",10,True,""],
["IIP","Index of Industrial Production","Growth","MOSPI","Monthly","Index","MOSPI",11,True,""],
["FII","FII Net Flow","Flows","NSDL","Daily","₹ Cr","NSDL",12,True,""],
["DII","DII Net Flow","Flows","NSDL","Daily","₹ Cr","NSDL",13,True,""],
["INDIAVIX","India VIX","Volatility","NSE","Daily","Index","NSE",14,True,""],
["GSEC10Y","10Y Bond Yield","Rates","RBI","Daily","%","RBI",15,True,""]

]

def main():
    write_csv("broad_market.csv", HEADER, broad_market)
    write_csv("sectors.csv", HEADER, sectors)
    write_csv("industries.csv", HEADER, industries)
    write_csv("themes.csv", HEADER, themes)
    write_csv("factors.csv", HEADER, factors)
    write_csv("fixed_income.csv", HEADER, fixed_income)
    write_csv("commodities.csv", HEADER, commodities)
    write_csv("macro.csv", MACRO_HEADER, macro)


if __name__ == "__main__":
    main()
