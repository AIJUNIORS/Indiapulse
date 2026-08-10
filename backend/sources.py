"""
sources.py -- IndiaPulse category -> instrument candidate registry (v3.1 S9)

This is the STATIC catalog of known candidate instruments per category: ETF,
benchmark index, composite constituents, or direct futures/FX series. It does
NOT decide what gets used -- data_hierarchy.resolve_source() does that, applying
the 3yr-floor hierarchy (v3.1 S2.2) on top of whatever is registered here.

Maintenance model: edited by PR only, never by automation. Add a candidate when
a new ETF launches, a ticker changes, or a benchmark/composite needs updating.
History-years figures are point-in-time and drift forward with the calendar --
re-verify periodically rather than treating them as permanently accurate.

`verified=False` marks a candidate whose constituents/history are inferred/
proposed rather than confirmed against a live data pull -- resolve_source()
will still use it (better than "unresolved"), but it should surface distinctly
in any report/diff output until someone confirms it.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class InstrumentCandidate:
    kind: str                          # 'etf' | 'benchmark' | 'composite' | 'futures' | 'fx'
    source_type_label: str              # exact display label, matches the frontend's RAW sourceType strings
    history_years: float
    symbol: Optional[str] = None        # for etf / benchmark / futures / fx
    constituents: Optional[tuple] = None  # for composite
    return_basis: str = 'unknown'       # 'TRI' | 'price_only' | 'na' -- v3.1 S2.3
    verified: bool = True
    note: str = ''


@dataclass(frozen=True)
class CategorySource:
    group: str
    name: str
    flag: Optional[str] = None          # 'context' | 'currency' | None
    candidates: dict = field(default_factory=dict)  # {kind: InstrumentCandidate}


CATEGORY_SOURCES: list[CategorySource] = [

    # ----------------------------------------------------------------------
    # broad-market
    # ----------------------------------------------------------------------
    CategorySource(
        group='broad-market', name='Nifty 50', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=17.6, symbol='NIFTYBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='broad-market', name='Nifty Next 50', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=17.6, symbol='JUNIORBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='broad-market', name='Nifty 100', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=13.3, symbol='NIF100BEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='broad-market', name='Nifty 500', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=20.8, symbol='^CRSLDX', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='broad-market', name='Sensex', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=8.2, symbol='HDFCSENSEX.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='broad-market', name='BSE 500', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=3.4, symbol='HDFCBSE500.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='broad-market', name='India VIX', flag='context',
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=18.4, symbol='^INDIAVIX', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='broad-market', name='USD/INR', flag='currency',
        candidates={
            'fx': InstrumentCandidate(kind='fx', source_type_label='FX', history_years=22.7, symbol='INR=X', return_basis='na', verified=True),
        },
    ),
    CategorySource(
        group='broad-market', name='Large & Mid Cap', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=18.9, symbol='NIFTY_LARGEMID250.NS', return_basis='TRI', verified=True),
        },
    ),

    # ----------------------------------------------------------------------
    # market-cap
    # ----------------------------------------------------------------------
    CategorySource(
        group='market-cap', name='Large Cap', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=17.6, symbol='NIFTYBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='market-cap', name='Mid Cap', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=15.5, symbol='MOM100.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='market-cap', name='Small Cap', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=3.4, symbol='HDFCSML250.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='market-cap', name='Micro Cap', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=15.2, symbol='NIFTY_MICROCAP250.NS', return_basis='TRI', verified=True),
        },
    ),

    # ----------------------------------------------------------------------
    # sector
    # ----------------------------------------------------------------------
    CategorySource(
        group='sector', name='Banking', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=17.6, symbol='BANKBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Private Banks', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=7.0, symbol='PVTBANIETF.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='PSU Banks', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=17.6, symbol='PSUBNKBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Financial Services', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=24.1, constituents=('HDFCBANK', 'ICICIBANK', 'BAJFINANCE', 'SBIN', 'KOTAKBANK'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Information Technology', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=6.1, symbol='ITBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Pharma', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=5.1, symbol='PHARMABEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Healthcare', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=4.0, symbol='MOHEALTH.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='FMCG', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=5.0, symbol='FMCGIETF.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Auto', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=4.5, symbol='AUTOBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Infrastructure', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=15.8, symbol='INFRABEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Metals', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=15.0, symbol='^CNXMETAL', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Energy', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=15.5, symbol='^CNXENERGY', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Oil & Gas', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=29.3, constituents=('RELIANCE', 'ONGC', 'IOC', 'BPCL', 'GAIL'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Power', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=16.6, constituents=('NTPC', 'POWERGRID', 'TATAPOWER', 'ADANIPOWER', 'JSWENERGY'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Realty', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=16.0, symbol='^CNXREALTY', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Telecom', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=24.1, constituents=('BHARTIARTL', 'IDEA', 'TTML'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='sector', name='Manufacturing', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=24.1, constituents=('LT', 'ABB', 'SIEMENS', 'M&M', 'POLYCAB'), return_basis='price_only', verified=True),
        },
    ),

    # ----------------------------------------------------------------------
    # theme
    # ----------------------------------------------------------------------
    CategorySource(
        group='theme', name='Defence', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=5.8, constituents=('HAL', 'BEL', 'SOLARINDS', 'MAZDOCK', 'BDL'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='theme', name='PSU', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=15.7, constituents=('ONGC', 'NTPC', 'POWERGRID', 'COALINDIA', 'SBIN'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='theme', name='CPSE', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=12.3, symbol='CPSEETF.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='theme', name='Bharat 22', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=6.6, symbol='ICICIB22.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='theme', name='Digital India', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=4.3, symbol='TNIDETF.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='theme', name='ESG', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=24.0, constituents=('HDFCBANK', 'INFY', 'ICICIBANK', 'TCS', 'HINDUNILVR'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='theme', name='Tourism', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=6.8, constituents=('INDHOTEL', 'INDIGO', 'IRCTC', 'THOMASCOOK', 'CHALET'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='theme', name='Innovation', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=24.1, constituents=('TCS', 'INFY', 'WIPRO', 'HCLTECH'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='theme', name='Consumption', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=12.3, symbol='CONSUMBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='theme', name='Capital Markets', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=5.8, constituents=('BSE', 'CDSL', 'HDFCAMC', 'NAM-INDIA', 'ANGELONE'), return_basis='price_only', verified=True),
        },
    ),

    # ----------------------------------------------------------------------
    # strategy
    # ----------------------------------------------------------------------
    CategorySource(
        group='strategy', name='Quality', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=3.9, symbol='NIFTYQLITY.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='strategy', name='Value', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=11.1, symbol='NV20BEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='strategy', name='Alpha', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=4.6, symbol='ALPHA.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='strategy', name='Low Volatility', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=8.2, symbol='LOWVOLIETF.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='strategy', name='Alpha Low Volatility', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=5.9, symbol='ALPL30IETF.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='strategy', name='Momentum', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=15.2, symbol='NIFTY200_MOMENTUM30.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='strategy', name='Momentum Quality', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF Proxy', history_years=6.2, symbol='MOM30IETF.NS', return_basis='TRI', verified=True),
        },
    ),

    # ----------------------------------------------------------------------
    # commodities
    # ----------------------------------------------------------------------
    CategorySource(
        group='commodities', name='Gold', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=17.6, symbol='GOLDBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='commodities', name='Silver', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=4.5, symbol='SILVERBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='commodities', name='Copper', flag=None,
        candidates={
            'futures': InstrumentCandidate(kind='futures', source_type_label='Futures', history_years=25.9, symbol='HG=F', return_basis='na', verified=True),
        },
    ),
    CategorySource(
        group='commodities', name='Crude Oil', flag=None,
        candidates={
            'futures': InstrumentCandidate(kind='futures', source_type_label='Futures', history_years=25.9, symbol='CL=F', return_basis='na', verified=True),
        },
    ),
    CategorySource(
        group='commodities', name='Natural Gas', flag=None,
        candidates={
            'futures': InstrumentCandidate(kind='futures', source_type_label='Futures', history_years=25.9, symbol='NG=F', return_basis='na', verified=True),
        },
    ),

    # ----------------------------------------------------------------------
    # global-markets
    # ----------------------------------------------------------------------
    CategorySource(
        group='global-markets', name='Euro Stoxx 50', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=19.3, symbol='^STOXX50E', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Nikkei 225', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=61.6, symbol='^N225', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='CSI 300', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=5.4, symbol='000300.SS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Hang Seng', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=16.4, symbol='HNGSNGBEES.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Taiwan (TAIEX)', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=29.1, symbol='^TWII', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='South Korea (KOSPI)', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=29.6, symbol='^KS11', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Indonesia (IDX)', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=36.3, symbol='^JKSE', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Thailand (SET)', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=29.6, symbol='^SET.BK', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Middle East (Tadawul)', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=27.8, symbol='^TASI.SR', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Brazil (Bovespa)', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=33.3, symbol='^BVSP', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Vietnam', flag=None,
        candidates={
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=19.5, constituents=('VNM', 'EIB.VN', 'SSI.VN'), return_basis='price_only', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Mexico (S&P/BMV IPC)', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=34.7, symbol='^MXX', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='global-markets', name='Africa (FTSE/JSE Top 40)', flag=None,
        candidates={
            'benchmark': InstrumentCandidate(kind='benchmark', source_type_label='Index', history_years=31.1, symbol='^J200.JO', return_basis='TRI', verified=True),
        },
    ),

    # ----------------------------------------------------------------------
    # emerging
    # ----------------------------------------------------------------------
    CategorySource(
        group='emerging', name='Cement', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=1.1, symbol='CEMNTGROWW.NS', return_basis='TRI', verified=True),
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=24.1, constituents=('ULTRACEMCO', 'SHREECEM', 'AMBUJACEM', 'ACC', 'DALBHARAT'), return_basis='price_only', verified=False, note='Proposed fallback -- Cement ETF is sub-3yr (1.1y); constituents not yet confirmed'),
        },
    ),
    CategorySource(
        group='emerging', name='Railways', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=1.1, symbol='GROWWRAIL.NS', return_basis='TRI', verified=True),
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=24.1, constituents=('IRCTC', 'RVNL', 'IRFC', 'RAILTEL', 'TITAGARH'), return_basis='price_only', verified=False, note='Proposed fallback -- Railways ETF is sub-3yr (1.1y); constituents not yet confirmed'),
        },
    ),
    CategorySource(
        group='emerging', name='EV Ecosystem', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=2.1, symbol='EVIETF.NS', return_basis='TRI', verified=True),
            'composite': InstrumentCandidate(kind='composite', source_type_label='Composite', history_years=24.1, constituents=('TMPV', 'M&M', 'BAJAJ-AUTO', 'EXIDEIND', 'ARE&M'), return_basis='price_only', verified=False, note='Proposed fallback -- EV Ecosystem ETF is sub-3yr (2.1y); constituents not yet confirmed. NSE renamed AMARAJABAT -> ARE&M, Oct 2023. TATAMOTORS swapped for TMPV (Tata Motors Passenger Vehicles Ltd, demerged entity housing Nexon EV/Punch EV/Tiago EV -- the direct EV-demand proxy vs. the parent commercial-vehicle-weighted entity) -- TMPV is newly listed post-demerger, likely well under the 3yr floor itself; verify actual listing date, exact Yahoo ticker, and history length via the local check script before trusting this in the composite.'),
        },
    ),
    CategorySource(
        group='emerging', name='Chemicals', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=3.1, symbol='CHEMICAL.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='emerging', name='Insurance', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=3.4, symbol='ECAPINSURE.NS', return_basis='TRI', verified=True),
        },
    ),
    CategorySource(
        group='emerging', name='Logistics', flag=None,
        candidates={
            'etf': InstrumentCandidate(kind='etf', source_type_label='ETF', history_years=3.4, symbol='INFRA.NS', return_basis='TRI', verified=True),
        },
    ),
]


def get(group: str, name: str) -> CategorySource:
    for c in CATEGORY_SOURCES:
        if c.group == group and c.name == name:
            return c
    raise KeyError(f"No source registered for {group}/{name} -- add it via PR before referencing it")

