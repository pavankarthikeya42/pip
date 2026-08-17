from app.browser.selectors import LOGIN_EMAIL, LOGIN_PASSWORD, ASK_KARI_BUTTON, SOURCE_NAME


def test_login_selectors_match_supplied_html():
    assert LOGIN_EMAIL == '#email'
    assert LOGIN_PASSWORD == '#password'


def test_ask_kari_and_source_selectors_are_stable():
    assert 'Ask KARI' in ASK_KARI_BUTTON
    assert SOURCE_NAME == 'span.src-name'
