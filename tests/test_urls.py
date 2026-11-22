from scamshield.urls import analyze_urls, strip_urls


def one(text):
    urls = analyze_urls(text)
    assert len(urls) == 1, urls
    return urls[0]


def test_shortener_flagged():
    assert "shortener" in one("pay at https://bit.ly/abc").flags


def test_ip_host_flagged():
    assert "ip_host" in one("go to http://10.0.0.5/login").flags


def test_userinfo_trick_flagged_and_real_host_used():
    u = one("https://dhl.com@evil-site.top/x")
    assert "userinfo_trick" in u.flags
    assert u.host == "evil-site.top"


def test_lookalike_brand_flagged():
    assert "lookalike_brand:dhl" in one("https://dhl-parcel-uae.top/track").flags


def test_subdomain_trick_is_lookalike():
    assert any(f.startswith("lookalike_brand") for f in one("https://dhl.com.evil.top/").flags)


def test_official_domains_not_flagged():
    for text, brand in [
        ("https://www.dhl.com/ae-en/home/tracking.html", "dhl"),
        ("https://dhl.ae/track", "dhl"),
        ("https://www.adcustoms.gov.ae/en", "abu_dhabi_customs"),
        ("https://www.centralbank.ae/en", "cbuae"),
    ]:
        u = one(text)
        assert u.official_brand == brand, text
        assert not u.flags, (text, u.flags)


def test_bare_domain_found_and_trailing_punctuation_stripped():
    u = one("visit abudhabi-customs-fee.com/pay.")
    assert u.host == "abudhabi-customs-fee.com"


def test_plain_text_is_not_a_url():
    assert analyze_urls("Paid Dh3.50, see e.g. page 2. Email me at a@b.com") == []


def test_display_is_defanged():
    assert one("http://evil.top/x").display == "hxxp://evil[.]top/x"


def test_strip_urls_removes_words_inside_domains():
    assert "fee" not in strip_urls("pay now abudhabi-customs-fee.com/pay")
