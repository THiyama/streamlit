# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2024)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from typing import NoReturn

import streamlit as st
from streamlit import source_util
from streamlit.deprecation_util import make_deprecated_name_warning
from streamlit.errors import NoSessionContext, StreamlitAPIException
from streamlit.logger import get_logger
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner import RerunData, get_script_run_ctx

_LOGGER = get_logger(__name__)


@gather_metrics("stop")
def stop() -> NoReturn:  # type: ignore[misc]
    """Stops execution immediately.

    Streamlit will not run any statements after `st.stop()`.
    We recommend rendering a message to explain why the script has stopped.

    Example
    -------
    >>> import streamlit as st
    >>>
    >>> name = st.text_input('Name')
    >>> if not name:
    >>>   st.warning('Please input a name.')
    >>>   st.stop()
    >>> st.success('Thank you for inputting a name.')

    """
    ctx = get_script_run_ctx()

    if ctx and ctx.script_requests:
        ctx.script_requests.request_stop()
        # Force a yield point so the runner can stop
        st.empty()


@gather_metrics("rerun")
def rerun() -> NoReturn:  # type: ignore[misc]
    """Rerun the script immediately.

    When `st.rerun()` is called, the script is halted - no more statements will
    be run, and the script will be queued to re-run from the top.
    """

    ctx = get_script_run_ctx()

    if ctx and ctx.script_requests:
        query_string = ctx.query_string
        page_script_hash = ctx.page_script_hash

        ctx.script_requests.request_rerun(
            RerunData(
                query_string=query_string,
                page_script_hash=page_script_hash,
            )
        )
        # Force a yield point so the runner can do the rerun
        st.empty()


@gather_metrics("experimental_rerun")
def experimental_rerun() -> NoReturn:
    """Rerun the script immediately.

    When `st.experimental_rerun()` is called, the script is halted - no
    more statements will be run, and the script will be queued to re-run
    from the top.
    """
    msg = make_deprecated_name_warning("experimental_rerun", "rerun", "2024-04-01")
    # Log warning before the rerun, or else it would be interrupted
    # by the rerun. We do not send a frontend warning because it wouldn't
    # be seen.
    _LOGGER.warning(msg)
    rerun()


@gather_metrics("switch_page")
def switch_page(page: str) -> NoReturn:  # type: ignore[misc]
    """Switch the current programmatically page in a multi-page app.
    When `st.switch_page()` is called with a page, the current page script is halted
    and the requested page script will be queued to run from the top.
    Parameters
    ----------
    page: str
        The file path, relative to the main script, of the page to switch to.
    """

    ctx = get_script_run_ctx()

    if not ctx or not ctx.script_requests:
        # This should never be the case
        raise NoSessionContext()

    main_script_path = os.path.join(os.getcwd(), ctx.main_script_path)
    main_script_directory = os.path.dirname(main_script_path)

    # Convenience for handling ./ notation and ensure leading / doesn't refer to root directory
    page = os.path.normpath(page.strip("/"))

    # Build full path
    requested_page = os.path.join(main_script_directory, page)
    all_app_pages = source_util.get_pages(ctx.main_script_path).values()

    matched_pages = [p for p in all_app_pages if p["script_path"] == requested_page]

    if len(matched_pages) == 0:
        raise StreamlitAPIException(
            f"Could not find page: '{page}'. Must be the file path relative to the main script, from the directory: {os.path.basename(main_script_directory)}."
        )

    ctx.script_requests.request_rerun(
        RerunData(
            query_string="",
            page_script_hash=matched_pages[0]["page_script_hash"],
        )
    )
    # Force a yield point so the runner can do the rerun
    st.empty()
