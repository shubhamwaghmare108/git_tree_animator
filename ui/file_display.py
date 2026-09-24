"""
Display file state: working tree, staging area, commits.
"""

import streamlit as st
from git_simulator.state import IndexState, WorkingTreeState, GitState


def render_staging_area(index: IndexState) -> None:
    """Display files in staging area (index)."""
    if not index.staged_files:
        st.markdown("*No staged changes*")
    else:
        st.markdown(f"**{len(index.staged_files)} file(s) staged**")
        for filename in sorted(index.staged_files.keys()):
            st.markdown(f"  ✓ `{filename}`")


def render_working_tree(wt: WorkingTreeState) -> None:
    """Display changes in working directory."""
    total_changes = len(wt.modified_files) + len(wt.new_files) + len(wt.deleted_files)
    
    if total_changes == 0:
        st.markdown("*Working tree clean*")
    else:
        st.markdown(f"**{total_changes} file(s) changed**")
        
        if wt.modified_files:
            st.markdown("*Modified:*")
            for filename in sorted(wt.modified_files.keys()):
                st.markdown(f"  ~ `{filename}`")
        
        if wt.new_files:
            st.markdown("*New files:*")
            for filename in sorted(wt.new_files.keys()):
                st.markdown(f"  + `{filename}`")
        
        if wt.deleted_files:
            st.markdown("*Deleted:*")
            for filename in sorted(wt.deleted_files):
                st.markdown(f"  - `{filename}`")


def render_repository_state(state: GitState) -> None:
    """Display overall repository state."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Commits", len(state.commits))
    
    with col2:
        st.metric("Branches", len(state.branches))
    
    with col3:
        st.metric("Reflog Entries", len(state.reflog))
    
    # Current HEAD status
    if state.head_is_detached:
        st.warning(f"🔀 **HEAD is detached** at `{state.head[:7]}`")
    else:
        st.info(f"📍 **On branch** `{state.head}`")


def render_commit_details(state: GitState) -> None:
    """Display details of the current commit."""
    current_sha = state.get_head_commit_sha()
    
    if not current_sha or current_sha not in state.commits:
        st.markdown("*No commits yet*")
        return
    
    commit = state.commits[current_sha]
    
    st.markdown(f"**Current Commit**")
    st.markdown(f"- **SHA**: `{commit.sha}`")
    st.markdown(f"- **Message**: {commit.message}")
    st.markdown(f"- **Author**: {commit.author}")
    
    if commit.parents:
        parent_shas = ", ".join(p[:7] for p in commit.parents)
        st.markdown(f"- **Parents**: `{parent_shas}`")
    else:
        st.markdown(f"- **Parents**: (root commit)")
