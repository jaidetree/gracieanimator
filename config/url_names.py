"""Route name constants, shared by ``config.urls`` (which registers them) and the
views/modules that ``reverse`` them.

Importing a name from here instead of repeating the raw string turns a typo into
a load-time ``AttributeError`` rather than a request-time ``NoReverseMatch``. A
separate module (not ``config.urls``) avoids a circular import, since
``config.urls`` already imports the view modules.

Note: a constant only guarantees the *symbol* exists, not that a ``path()`` is
registered for it — the test suite covers actual resolution.
"""

# Portfolio sections
ILLUSTRATION_GALLERY = "illustration_gallery"
SKETCHBOOK_SAMPLE_GALLERY = "sketchbook_sample_gallery"
COMICS_INDEX = "comics_index"
COMIC_DETAIL = "comic_detail"
COMIC_PAGE = "comic_page"
STORYBOARD_GALLERY = "storyboard_gallery"
STORYBOARD_CATEGORY = "storyboard_category"
STORYBOARD_DETAIL = "storyboard_detail"
STORYBOARD_AUTH = "storyboards_auth"
STORYBOARD_LOGOUT = "storyboards_logout"

# Pages
HOME = "home"
PAGE_DETAIL = "page_detail"
