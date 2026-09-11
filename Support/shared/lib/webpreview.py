"""Python bindings for webpreview.sh, the shared HTML output header and footer."""

import os

from tm_helpers import sh, sh_escape

WEBPREVIEW = sh_escape(os.path.join(os.environ["TM_SUPPORT_PATH"], "lib/webpreview.sh"))


def html_header(title, subtitle):
    return sh("source %s; html_header %s %s" % (WEBPREVIEW, sh_escape(title), sh_escape(subtitle)))


def html_footer():
    return sh("source %s; html_footer" % WEBPREVIEW)
