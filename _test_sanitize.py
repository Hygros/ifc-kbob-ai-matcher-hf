import nh3

html = '<div class="ai-map-group-label" data-guids="GUID1,GUID2" style="font-weight:bold;">Test</div>'
print("INPUT:", html)
print("DEFAULT nh3.clean:", nh3.clean(html))
print()

# Check how streamlit uses nh3
try:
    from streamlit.runtime.metrics_util import _clean_html
    print("Streamlit _clean_html:", _clean_html(html))
except Exception as e:
    print("_clean_html not available:", e)

# Check if streamlit has a sanitize function
import streamlit._main_utils as mu
print(dir(mu))
