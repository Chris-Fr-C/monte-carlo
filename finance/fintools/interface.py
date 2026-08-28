from enum import StrEnum
from typing import final
import polars as pl



type Symbol = str
"""Symbol of a stock. Example: NSNX"""


class Currency(StrEnum):
    """Currency value. 3 letter char."""
    EUR="EUR"
    CHF="CHF"
    USD="USD"

@final
class QuotesDf():
    type DataFrame = pl.DataFrame

    @final
    class Columns:
        TS="ts"
        """Timestamp"""
        SYMBOL="symbol"
        CURRENCY="currency"
        OPEN="open"
        CLOSE="close"
        HIGH="high"
        LOW="low"
        VOLUME="volume"
        DIVIDENDS="dividends"
        STOCK_SPLITS="stock_splits"




@final
class EnrichedQuotesDf():
    type DataFrame = pl.DataFrame

    @final
    class Columns:
        TS="ts"
        """Timestamp"""
        SYMBOL="symbol"
        CURRENCY="currency"
        OPEN="open"
        CLOSE="close"
        HIGH="high"
        LOW="low"
        VOLUME="volume"
        DIVIDENDS="dividends"
        STOCK_SPLITS="stock_splits"

        # and the crazy part
        VOLUME_ADI='volume_adi'
        VOLUME_OBV='volume_obv'
        VOLUME_CMF='volume_cmf'
        VOLUME_FI='volume_fi'
        VOLUME_EM='volume_em'
        VOLUME_SMA_EM='volume_sma_em'
        VOLUME_VPT='volume_vpt'
        VOLUME_VWAP='volume_vwap'
        VOLUME_MFI='volume_mfi'
        VOLUME_NVI='volume_nvi'
        VOLATILITY_BBM='volatility_bbm'
        VOLATILITY_BBH='volatility_bbh'
        VOLATILITY_BBL='volatility_bbl'
        VOLATILITY_BBW='volatility_bbw'
        VOLATILITY_BBP='volatility_bbp'
        VOLATILITY_BBHI='volatility_bbhi'
        VOLATILITY_BBLI='volatility_bbli'
        VOLATILITY_KCC='volatility_kcc'
        VOLATILITY_KCH='volatility_kch'
        VOLATILITY_KCL='volatility_kcl'
        VOLATILITY_KCW='volatility_kcw'
        VOLATILITY_KCP='volatility_kcp'
        VOLATILITY_KCHI='volatility_kchi'
        VOLATILITY_KCLI='volatility_kcli'
        VOLATILITY_DCL='volatility_dcl'
        VOLATILITY_DCH='volatility_dch'
        VOLATILITY_DCM='volatility_dcm'
        VOLATILITY_DCW='volatility_dcw'
        VOLATILITY_DCP='volatility_dcp'
        VOLATILITY_ATR='volatility_atr'
        VOLATILITY_UI='volatility_ui'
        TREND_MACD='trend_macd'
        TREND_MACD_SIGNAL='trend_macd_signal'
        TREND_MACD_DIFF='trend_macd_diff'
        TREND_SMA_FAST='trend_sma_fast'
        TREND_SMA_SLOW='trend_sma_slow'
        TREND_EMA_FAST='trend_ema_fast'
        TREND_EMA_SLOW='trend_ema_slow'
        TREND_VORTEX_IND_POS='trend_vortex_ind_pos'
        TREND_VORTEX_IND_NEG='trend_vortex_ind_neg'
        TREND_VORTEX_IND_DIFF='trend_vortex_ind_diff'
        TREND_TRIX='trend_trix'
        TREND_MASS_INDEX='trend_mass_index'
        TREND_DPO='trend_dpo'
        TREND_KST='trend_kst'
        TREND_KST_SIG='trend_kst_sig'
        TREND_KST_DIFF='trend_kst_diff'
        TREND_ICHIMOKU_CONV='trend_ichimoku_conv'
        TREND_ICHIMOKU_BASE='trend_ichimoku_base'
        TREND_ICHIMOKU_A='trend_ichimoku_a'
        TREND_ICHIMOKU_B='trend_ichimoku_b'
        TREND_STC='trend_stc'
        TREND_ADX='trend_adx'
        TREND_ADX_POS='trend_adx_pos'
        TREND_ADX_NEG='trend_adx_neg'
        TREND_CCI='trend_cci'
        TREND_VISUAL_ICHIMOKU_A='trend_visual_ichimoku_a'
        TREND_VISUAL_ICHIMOKU_B='trend_visual_ichimoku_b'
        TREND_AROON_UP='trend_aroon_up'
        TREND_AROON_DOWN='trend_aroon_down'
        TREND_AROON_IND='trend_aroon_ind'
        TREND_PSAR_UP='trend_psar_up'
        TREND_PSAR_DOWN='trend_psar_down'
        TREND_PSAR_UP_INDICATOR='trend_psar_up_indicator'
        TREND_PSAR_DOWN_INDICATOR='trend_psar_down_indicator'
        MOMENTUM_RSI='momentum_rsi'
        MOMENTUM_STOCH_RSI='momentum_stoch_rsi'
        MOMENTUM_STOCH_RSI_K='momentum_stoch_rsi_k'
        MOMENTUM_STOCH_RSI_D='momentum_stoch_rsi_d'
        MOMENTUM_TSI='momentum_tsi'
        MOMENTUM_UO='momentum_uo'
        MOMENTUM_STOCH='momentum_stoch'
        MOMENTUM_STOCH_SIGNAL='momentum_stoch_signal'
        MOMENTUM_WR='momentum_wr'
        MOMENTUM_AO='momentum_ao'
        MOMENTUM_ROC='momentum_roc'
        MOMENTUM_PPO='momentum_ppo'
        MOMENTUM_PPO_SIGNAL='momentum_ppo_signal'
        MOMENTUM_PPO_HIST='momentum_ppo_hist'
        MOMENTUM_PVO='momentum_pvo'
        MOMENTUM_PVO_SIGNAL='momentum_pvo_signal'
        MOMENTUM_PVO_HIST='momentum_pvo_hist'
        MOMENTUM_KAMA='momentum_kama'
        OTHERS_DR='others_dr'
        OTHERS_DLR='others_dlr'
        OTHERS_CR='others_cr'
