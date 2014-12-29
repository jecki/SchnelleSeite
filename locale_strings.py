

import os


fourletter = [
    "aa_DJ", "aa_ER", "aa_ET", "ae_CH", "af_ZA", "ag_IN", "ai_IN", "ak_GH",
    "ak_TW", "al_ET", "am_ET", "an_ES", "an_TW", "ap_AN", "ap_AW", "ap_CW",
    "ar_AE", "ar_BH", "ar_DZ", "ar_EG", "ar_IN", "ar_IQ", "ar_JO", "ar_KW",
    "ar_LB", "ar_LY", "ar_MA", "ar_OM", "ar_QA", "ar_SA", "ar_SD", "ar_SS",
    "ar_SY", "ar_TN", "ar_YE", "as_IN", "at_IN", "az_AZ", "be_BY", "bg_BG",
    "bn_BD", "bn_IN", "bo_CN", "bo_IN", "br_FR", "bs_BA", "ca_AD", "ca_ES",
    "ca_FR", "ca_IT", "cs_CZ", "cv_RU", "cy_GB", "da_DK", "de_AT", "de_BE",
    "de_CH", "de_DE", "de_LU", "ds_DE", "ds_NL", "dv_MV", "dz_BT", "el_CY",
    "el_GR", "em_ZM", "en_AG", "en_AU", "en_BW", "en_CA", "en_DK", "en_GB",
    "en_HK", "en_IE", "en_IN", "en_NG", "en_NZ", "en_PH", "en_SG", "en_US",
    "en_ZA", "en_ZM", "en_ZW", "er_DZ", "er_MA", "es_AR", "es_BO", "es_CL",
    "es_CO", "es_CR", "es_CU", "es_DO", "es_EC", "es_ES", "es_GT", "es_HN",
    "es_MX", "es_NI", "es_PA", "es_PE", "es_PR", "es_PY", "es_SV", "es_US",
    "es_UY", "es_VE", "et_EE", "eu_ES", "ez_ER", "ez_ET", "fa_IR", "ff_SN",
    "fi_FI", "fo_FO", "fr_BE", "fr_CA", "fr_CH", "fr_FR", "fr_LU", "fy_DE",
    "fy_NL", "ga_IE", "gd_GB", "gl_ES", "gu_IN", "gv_GB", "ha_NG", "he_IL",
    "he_NP", "hi_IN", "hn_MX", "ho_IN", "hr_HR", "hr_RU", "hs_CA", "ht_HT",
    "hu_HU", "hy_AM", "ia_FR", "id_ET", "id_ID", "ig_ER", "ig_NG", "ij_IT",
    "ik_CA", "il_PH", "is_IS", "it_CH", "it_IT", "iu_CA", "iu_NU", "iu_NZ",
    "iw_IL", "ja_JP", "ka_GE", "kk_KZ", "kl_GL", "km_KH", "kn_IN", "ko_KR",
    "ks_IN", "ku_TR", "kw_GB", "ky_KG", "lb_LU", "lg_UG", "li_BE", "li_NL",
    "lo_LA", "lt_LT", "lv_LV", "mg_MG", "mi_NZ", "mk_MK", "ml_IN", "mn_MN",
    "mn_TW", "mr_IN", "ms_MY", "mt_MT", "my_MM", "nb_NO", "ne_IN", "ne_NP",
    "ni_IN", "nl_AW", "nl_BE", "nl_NL", "nm_US", "nn_NO", "np_IN", "nr_ZA",
    "oc_FR", "oi_IN", "ok_IN", "om_ET", "om_KE", "or_IN", "os_RU", "pa_IN",
    "pa_PK", "pl_PL", "ps_AF", "pt_BR", "pt_PT", "rh_UA", "ro_RO", "ru_RU",
    "ru_UA", "rw_RW", "rx_IN", "sa_IN", "sb_DE", "sb_PL", "sc_IT", "sd_IN",
    "se_NO", "si_LK", "sk_SK", "sl_SI", "so_DJ", "so_ET", "so_KE", "so_SO",
    "so_ZA", "sq_AL", "sq_MK", "sr_ME", "sr_RS", "ss_ZA", "st_ES", "st_ZA",
    "sv_FI", "sv_SE", "sw_KE", "sw_TZ", "ta_IN", "ta_LK", "te_IN", "tg_TJ",
    "th_TH", "ti_ER", "ti_ET", "tk_TM", "tl_PH", "tn_ZA", "tr_CY", "tr_TR",
    "ts_ZA", "tt_RU", "ue_HK", "ug_CN", "uk_UA", "ur_IN", "ur_IT", "ur_PK",
    "uz_PE", "uz_UZ", "ve_ZA", "vi_VN", "wa_BE", "wo_SN", "xh_ZA", "yc_PE",
    "yi_US", "yn_ER", "yo_NG", "zh_CN", "zh_HK", "zh_SG", "zh_TW", "zl_PL",
    "zu_ZA"
]
fourletter_set = set(fourletter)

twoletter = [
    "AA", "AE", "AF", "AG", "AI", "AK", "AL", "AM", "AN", "AP", "AR", "AS",
    "AT", "AZ", "BE", "BG", "BN", "BO", "BR", "BS", "CA", "CS", "CV", "CY",
    "DA", "DE", "DS", "DV", "DZ", "EL", "EM", "EN", "ER", "ES", "ET", "EU",
    "EZ", "FA", "FF", "FI", "FO", "FR", "FY", "GA", "GD", "GL", "GU", "GV",
    "HA", "HE", "HI", "HN", "HO", "HR", "HS", "HT", "HU", "HY", "IA", "ID",
    "IG", "IJ", "IK", "IL", "IS", "IT", "IU", "IW", "JA", "KA", "KK", "KL",
    "KM", "KN", "KO", "KS", "KU", "KW", "KY", "LB", "LG", "LI", "LO", "LT",
    "LV", "MG", "MI", "MK", "ML", "MN", "MR", "MS", "MT", "MY", "NB", "NE",
    "NI", "NL", "NM", "NN", "NP", "NR", "OC", "OI", "OK", "OM", "OR", "OS",
    "PA", "PL", "PS", "PT", "RH", "RO", "RU", "RW", "RX", "SA", "SB", "SC",
    "SD", "SE", "SI", "SK", "SL", "SO", "SQ", "SR", "SS", "ST", "SV", "SW",
    "TA", "TE", "TG", "TH", "TI", "TK", "TL", "TN", "TR", "TS", "TT", "UE",
    "UG", "UK", "UR", "UZ", "VE", "VI", "WA", "WO", "XH", "YC", "YI", "YN",
    "YO", "ZH", "ZL", "ZU"
]
twoletter_set = set(twoletter)


class LocaleError(Exception):

    def __init__(self, locale_str):
        Exception.__init__(self, "%s is not a valid locale" % locale_str)


def valid_locale(locale_str, raise_error=False):
    """Returns True if locale_str represents a valid locale. Otherwise,
    returns False or raises an error depending on raise_error.
    """
    if (locale_str in fourletter_set or locale_str in twoletter_set or
            locale_str == 'ANY'):
        return True
    else:
        if raise_error:
            raise LocaleError(locale_str)
    return False


def narrow_match(requested, available):
    """Finds the best match for the requested language in a set of available
    languages.

    Raises a KeyError if no match was found.
    Raises a ValueError if no languages are available at all.
    """
    assert requested == 'ANY' or len(requested) in [2, 5], \
        str(requested) + " is not a valid language code!"
    if not available:
        raise ValueError("No variants available!")
    if requested in available:
        return requested
    if 'ANY' in available:
        return 'ANY'
    if requested == 'ANY':
        av_list = list(available)
        av_list.sort()
        return av_list[0]
    if len(requested) > 2:
        reduced_requested = requested[0:2].upper()
        reduced_available = {av[0:2].upper(): av for av in available
                             if av != 'ANY'}
        if reduced_requested in reduced_available:
            return reduced_available[reduced_requested]
    raise KeyError("No match for {0!s} in {1!s}".format(requested, available))


def match(requested, available, substitution_list):
    """Finds the best match for the requested language in a set of available
    languages, but allows to pick a substitute if not match was found.

    Raises a KeyError if not even an item from the substitution list is matches
    (narrowly) the available languages.
    """
    try:
        return narrow_match(requested, available)
    except KeyError:
        for substitute in substitution_list:
            try:
                return narrow_match(substitute, available)
            except KeyError:
                pass
    raise KeyError("No match found for {0!s} or any of {1!s} in {2!s}".format(
                   requested, substitution_list, available))


def get_locale(name):
    """Retrieve locale information from a file or directory name.

    Parameters:
        name(str): file or directory basename (i.e. without any extensions)
    Returns:
        locale information (string) or empty string if the name does not
        contain any locale information
    Raises:
        LocaleError
    """
    L = len(name)
    if L > 4 and name[-4:].upper() == "_ANY":
        return 'ANY'
    if L > 6 and name[-6] == "_" and name[-3] == "_":
        lc = name[-5:]
        if lc in fourletter_set:
            return lc
        elif name[-5:-3].islower() and name[-2:].isupper():
            raise LocaleError("%s in file %s" % (lc, name))
    if L > 3 and name[-3] == "_":
        lc = name[-2:]
        if lc in twoletter_set:
            return lc
        elif lc.isalpha():
            raise LocaleError("%s in file %s" % (lc, name))
    return ''


def extract_locale(filepath):
    """Extracts locale information from filename or parent directory.
    Returns locale string or 'any'.

    Locale information is assumed to reside at the end of the basename of the
    file, right before the extension. It must either have the form "_xx_XX" or
    "_XX", eg. "_de_DE" or simply "_DE", and represent a valid locale.

    If no locale information is found in the file name the names of the parent
    directory are checked inward out for locale information.

    An error is reported, if there appears to be locale information
    but if it is malformed.

    An empty string is returned if no (intended) locale information seems to be
    present in the filename or any of the parent directories' names.
    """
    parent, path = os.path.split(filepath)
    while path:
        pos = path.rfind('.')
        basename = path[:pos] if pos >= 0 else path
        locale = get_locale(basename)
        if locale:
            return locale
        parent, path = os.path.split(parent)
    return ''


def remove_locale(name):
    """Returns file or directory name with locale information removed.
    """
    assert name.find(os.path.sep) == -1
    pos = name.rfind(".")
    basename = name[:pos] if pos >= 0 else name
    locale = get_locale(basename)
    if locale:
        return basename[:-len(locale) - 1] + (name[pos:] if pos >= 0 else "")
    else:
        return name
