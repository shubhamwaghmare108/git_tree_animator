"""
Git Tree Animator - Main Streamlit Application

Run with: streamlit run ui/app.py
"""

import streamlit as st
from git_simulator.repository import GitRepository
from git_simulator.state import WorkingTreeState
from ui.graph_renderer import render_git_graph, render_git_animation
from ui.file_display import render_staging_area, render_working_tree, render_repository_state, render_commit_details


# Page configuration
st.set_page_config(
    page_title="Git Tree Animator",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .command-success { color: #2ecc71; font-family: monospace; }
    .command-error { color: #e74c3c; font-family: monospace; }
    .command-input { font-family: monospace; }
    .legend {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 5px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# PAGE TITLE
# ============================================================================

st.title("🌳 Git Tree Animator")
st.markdown("*Visually understand how Git commands affect your repository*")

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    education_mode = st.selectbox(
        "Education Mode",
        ["Beginner", "Intermediate", "Advanced"],
        help="Beginner: Commits, branches, HEAD | Intermediate: + merge, reset, restore | Advanced: + rebase, remote, reflog"
    )
    
    animation_speed = st.slider(
        "Animation Speed",
        0.5, 4.0, 1.0, 0.5,
        help="Speed multiplier for animations"
    )
    
    st.markdown("---")
    st.markdown("## 📚 Lessons")
    
    lesson_col1, lesson_col2 = st.columns(2)
    
    with lesson_col1:
        if st.button("📖 Basic Git", use_container_width=True):
            st.session_state.lesson_commands = [
                "git init",
                "git add .",
                "git commit -m \"Initial commit\"",
            ]
            st.session_state.lesson_name = "Basic Git"
    
    with lesson_col2:
        if st.button("📖 Branching", use_container_width=True):
            st.session_state.lesson_commands = [
                "git init",
                "git commit -m \"Main commit\"",
                "git branch feature",
                "git switch feature",
                "git commit -m \"Feature work\"",
            ]
            st.session_state.lesson_name = "Branching"
    
    if st.button("📖 Merge", use_container_width=True):
        st.session_state.lesson_commands = [
            "git init",
            "git commit -m \"Initial\"",
            "git branch feature",
            "git switch feature",
            "git commit -m \"Feature 1\"",
            "git commit -m \"Feature 2\"",
            "git switch main",
            "git merge feature",
        ]
        st.session_state.lesson_name = "Merge"
    
    if st.button("📖 Reset", use_container_width=True):
        st.session_state.lesson_commands = [
            "git init",
            "git commit -m \"Commit 1\"",
            "git commit -m \"Commit 2\"",
            "git reset --soft HEAD~1",
        ]
        st.session_state.lesson_name = "Reset"
    
    st.markdown("---")
    
    if st.button("🔄 Clear Everything", use_container_width=True):
        st.session_state.repo = GitRepository()
        st.session_state.lesson_commands = None
        st.rerun()

# ============================================================================
# INITIALIZE SESSION STATE
# ============================================================================

if "repo" not in st.session_state:
    st.session_state.repo = GitRepository()

if "lesson_commands" not in st.session_state:
    st.session_state.lesson_commands = None

if "lesson_name" not in st.session_state:
    st.session_state.lesson_name = None

# ============================================================================
# MAIN CONTENT AREA
# ============================================================================

# Show lesson if loaded
if st.session_state.lesson_commands:
    st.info(f"📖 **Lesson**: {st.session_state.lesson_name}")
    st.markdown("**Commands to execute:**")
    for i, cmd in enumerate(st.session_state.lesson_commands, 1):
        status = "✓" if i <= len(st.session_state.repo.history) else "○"
        st.code(f"{status} {cmd}")

# Main layout: Graph + State
col_graph, col_state = st.columns([2.5, 1.5])

with col_graph:
    st.markdown("### 📊 Commit Graph")
    if st.session_state.repo.history:
        history_states = [state for _, state in st.session_state.repo.history]
        fig = render_git_animation(history_states, animation_speed)
    else:
        fig = render_git_graph(st.session_state.repo.state)
    st.plotly_chart(fig, use_container_width=True, key="git_graph")

with col_state:
    st.markdown("### 📋 Repository State")
    render_repository_state(st.session_state.repo.state)
    
    st.markdown("#### Current Commit")
    render_commit_details(st.session_state.repo.state)
    
    st.markdown("#### Staging Area")
    render_staging_area(st.session_state.repo.state.index)
    
    st.markdown("#### Working Directory")
    render_working_tree(st.session_state.repo.state.working_tree)

# ============================================================================
# SIMULATED WORKING TREE EDITOR
# ============================================================================

st.markdown("---")
st.markdown("### 📝 Working Tree Editor")
st.caption("Edit simulated files, then use git add . and git commit to see a file snapshot move into the commit graph.")

edit_col1, edit_col2 = st.columns([1, 2])
with edit_col1:
    existing_files = sorted(
        set(st.session_state.repo.state.working_tree.modified_files)
        | set(st.session_state.repo.state.working_tree.new_files)
    )
    file_options = ["<new file>"] + existing_files
    selected_file = st.selectbox("File", file_options, key="editor_file")
    filename = st.text_input(
        "Filename",
        value="" if selected_file == "<new file>" else selected_file,
        key="editor_filename",
    )
with edit_col2:
    current_content = ""
    if selected_file != "<new file>":
        current_content = (
            st.session_state.repo.state.working_tree.modified_files.get(selected_file)
            or st.session_state.repo.state.working_tree.new_files.get(selected_file)
            or ""
        )
    content = st.text_area("Content", value=current_content, height=140, key="editor_content")

if st.button("💾 Save working-tree change"):
    if filename.strip():
        st.session_state.repo.set_working_file(filename.strip(), content)
        st.success(f"Working tree updated: {filename.strip()}")
        st.rerun()
    else:
        st.error("Enter a filename.")

# ============================================================================
# TAG WORKFLOW
# ============================================================================

st.markdown("---")
st.markdown("### 🏷️ Tags")
tag_state = st.session_state.repo.state
if tag_state.tags:
    for tag_name, tag_ptr in sorted(tag_state.tags.items()):
        kind = "annotated" if tag_ptr.annotated else "lightweight"
        st.caption(f"**{tag_name}** → {tag_ptr.target_sha[:7]} ({kind})")
        if tag_ptr.message:
            st.caption(f"  {tag_ptr.message}")
else:
    st.caption("No tags. Use `git tag v1.0` or `git tag -a v1.0 -m \"release\"`.")

# ============================================================================
# STASH WORKFLOW
# ============================================================================

st.markdown("---")
st.markdown("### 📦 Stash")
stash_state = st.session_state.repo.state
if stash_state.stashes:
    st.code("\n".join(f"{s.name}: {s.message}" for s in stash_state.stashes))
    stash_col1, stash_col2, stash_col3 = st.columns(3)
    with stash_col1:
        if st.button("📋 List stashes", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command("git stash list")
            st.info(message or "No stash entries.")
    with stash_col2:
        if st.button("📥 Apply latest", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command("git stash apply")
            st.error(message) if not success else st.success(message)
            st.rerun()
    with stash_col3:
        if st.button("📤 Pop latest", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command("git stash pop")
            st.error(message) if not success else st.success(message)
            st.rerun()
else:
    st.caption("No stashes. Edit a simulated file, then run git stash to save it for later.")

# ============================================================================
# REMOTE SYNCHRONIZATION
# ============================================================================

st.markdown("---")
st.markdown("### 🌐 Remote Repository")
if st.session_state.repo.state.remote_urls:
    for remote_name, url in sorted(st.session_state.repo.state.remote_urls.items()):
        st.caption(f"**{remote_name}** → {url}")
        tracking = st.session_state.repo.state.remotes.get(remote_name, {})
        server = st.session_state.repo.state.remote_servers.get(remote_name, {})
        remote_cols = st.columns([1, 1, 1])
        with remote_cols[0]:
            if st.button(f"⬇️ Fetch {remote_name}", key=f"fetch_{remote_name}"):
                success, message, _ = st.session_state.repo.execute_command(f"git fetch {remote_name}")
                st.error(message) if not success else st.success(message)
                st.rerun()
        with remote_cols[1]:
            if st.button(f"⬆️ Push current branch", key=f"push_{remote_name}"):
                branch = st.session_state.repo.state.head
                success, message, _ = st.session_state.repo.execute_command(f"git push {remote_name} {branch}")
                st.error(message) if not success else st.success(message)
                st.rerun()
        with remote_cols[2]:
            if st.button(f"🔄 Pull {remote_name}", key=f"pull_{remote_name}"):
                branch = st.session_state.repo.state.head
                success, message, _ = st.session_state.repo.execute_command(f"git pull {remote_name} {branch}")
                st.error(message) if not success else st.success(message)
                st.rerun()

        if tracking:
            st.write("**Local remote-tracking refs:**")
            st.code("\n".join(f"{remote_name}/{n} -> {p.target_sha[:7]}" for n, p in sorted(tracking.items())))
        elif server:
            st.caption("Remote has refs; run fetch to update local remote-tracking refs.")
else:
    st.info("No remotes configured. Try `git remote add origin https://example.com/student/demo.git`.")

# ============================================================================
# DETACHED HEAD / RECOVERY
# ============================================================================

if st.session_state.repo.state.head_is_detached:
    st.markdown("---")
    st.markdown("### 📍 Detached HEAD")
    detached_sha = st.session_state.repo.state.head
    st.warning(
        f"HEAD is detached at **{detached_sha[:7]}**. "
        "Commits made here are not attached to a branch."
    )
    st.caption("Switch to an existing branch to return to normal branch-based work.")

    branch_options = sorted(st.session_state.repo.state.branches)
    if branch_options:
        recovery_branch = st.selectbox(
            "Recover by switching to branch",
            branch_options,
            key="detached_recovery_branch",
        )
        if st.button("↩️ Switch back to branch", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command(
                f"git switch {recovery_branch}"
            )
            st.error(message) if not success else st.success(message)
            st.rerun()

# ============================================================================
# CHERRY-PICK WORKFLOW
# ============================================================================

if st.session_state.repo.state.cherry_pick_in_progress:
    st.markdown("---")
    st.markdown("### 🍒 Cherry-pick in Progress")
    cp_state = st.session_state.repo.state
    target = cp_state.cherry_pick_commit_sha
    if target and target in cp_state.commits:
        st.info(
            f"Applying **{target[:7]}** — {cp_state.commits[target].message}. "
            "Resolve conflicts, stage the result, then continue."
        )

    for conflict_file in sorted(cp_state.conflict_files):
        conflict_content = (
            cp_state.working_tree.modified_files.get(conflict_file, "")
            or cp_state.working_tree.new_files.get(conflict_file, "")
        )
        resolved = st.text_area(
            f"Resolve cherry-pick conflict: {conflict_file}",
            value=conflict_content,
            height=180,
            key=f"cherry_conflict_editor_{conflict_file}",
        )
        if st.button(
            f"💾 Save cherry-pick resolution: {conflict_file}",
            key=f"save_cherry_conflict_{conflict_file}",
        ):
            st.session_state.repo.set_working_file(conflict_file, resolved)
            st.success(f"Saved resolution for {conflict_file}. Run git add . next.")
            st.rerun()

    abort_col, continue_col = st.columns(2)
    with abort_col:
        if st.button("↩️ Abort cherry-pick", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command("git cherry-pick --abort")
            st.error(message) if not success else st.success(message)
            st.rerun()
    with continue_col:
        if st.button("🍒 Continue cherry-pick", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command("git cherry-pick --continue")
            st.error(message) if not success else st.success(message)
            st.rerun()

# ============================================================================
# REBASE WORKFLOW
# ============================================================================

if st.session_state.repo.state.rebase_in_progress:
    st.markdown("---")
    st.markdown("### 🔄 Rebase in Progress")
    rebase_state = st.session_state.repo.state
    current = rebase_state.rebase_current_commit
    pending = rebase_state.rebase_pending_commits
    if current and current in rebase_state.commits:
        st.info(
            f"Replaying **{current[:7]}** — {rebase_state.commits[current].message}. "
            f"Pending commits: {len(pending)}"
        )
    else:
        st.info(f"Rebase is replaying commits. Pending: {len(pending)}")

    if rebase_state.conflict_files:
        st.warning(
            "Resolve the conflicted files, save them, run git add ., "
            "then continue the rebase."
        )
        for conflict_file in sorted(rebase_state.conflict_files):
            conflict_content = (
                rebase_state.working_tree.modified_files.get(conflict_file, "")
                or rebase_state.working_tree.new_files.get(conflict_file, "")
            )
            resolved = st.text_area(
                f"Resolve rebase conflict: {conflict_file}",
                value=conflict_content,
                height=180,
                key=f"rebase_conflict_editor_{conflict_file}",
            )
            if st.button(
                f"💾 Save rebase resolution: {conflict_file}",
                key=f"save_rebase_conflict_{conflict_file}",
            ):
                st.session_state.repo.set_working_file(conflict_file, resolved)
                st.success(f"Saved resolution for {conflict_file}. Run git add . next.")
                st.rerun()

    abort_col, continue_col = st.columns(2)
    with abort_col:
        if st.button("↩️ Abort rebase", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command("git rebase --abort")
            st.error(message) if not success else st.success(message)
            st.rerun()
    with continue_col:
        if st.button("▶️ Continue rebase", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command("git rebase --continue")
            st.error(message) if not success else st.success(message)
            st.rerun()

# ============================================================================
# MERGE CONFLICT RESOLUTION
# ============================================================================

if st.session_state.repo.state.merge_in_progress:
    st.markdown("---")
    st.markdown("### ⚠️ Merge Conflict Resolution")
    st.warning("A merge is paused. Edit each conflicted file to remove the conflict markers, save it, then run git add . and git merge --continue.")
    for conflict_file in sorted(st.session_state.repo.state.conflict_files):
        conflict_content = st.session_state.repo.state.working_tree.modified_files.get(conflict_file, "")
        resolved = st.text_area(
            f"Resolve {conflict_file}",
            value=conflict_content,
            height=180,
            key=f"conflict_editor_{conflict_file}",
        )
        if st.button(f"💾 Save resolution: {conflict_file}", key=f"save_conflict_{conflict_file}"):
            st.session_state.repo.set_working_file(conflict_file, resolved)
            st.success(f"Saved resolution for {conflict_file}. Run git add . next.")
            st.rerun()

    abort_col, continue_col = st.columns(2)
    with abort_col:
        if st.button("↩️ Abort merge", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command("git merge --abort")
            st.error(message) if not success else st.success(message)
            st.rerun()
    with continue_col:
        if st.button("✅ Continue merge", use_container_width=True):
            success, message, _ = st.session_state.repo.execute_command("git merge --continue")
            st.error(message) if not success else st.success(message)
            st.rerun()

# ============================================================================
# COMMAND INPUT & EXECUTION
# ============================================================================

st.markdown("---")
st.markdown("### 💻 Terminal")

col_cmd, col_run, col_clear = st.columns([2, 0.8, 0.8])

with col_cmd:
    command_input = st.text_input(
        label="Command",
        placeholder="git commit -m 'message'",
        key="cmd_input",
        label_visibility="collapsed"
    )

with col_run:
    if st.button("▶ Run", use_container_width=True):
        if command_input:
            full_cmd = f"git {command_input}" if not command_input.startswith("git ") else command_input
            success, message, new_state = st.session_state.repo.execute_command(full_cmd)
            
            if success:
                st.success(message)
            else:
                st.error(message)
            
            st.rerun()

with col_clear:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.repo = GitRepository()
        st.session_state.lesson_commands = None
        st.rerun()

# ============================================================================
# COMMAND HISTORY TIMELINE
# ============================================================================

if st.session_state.repo.history:
    st.markdown("---")
    st.markdown("### 📜 Command History")
    
    history_cols = st.columns([1, 4, 1, 1])
    
    with history_cols[0]:
        st.markdown("**#**")
    with history_cols[1]:
        st.markdown("**Command**")
    with history_cols[2]:
        st.markdown("**Revert**")
    with history_cols[3]:
        st.markdown("**Details**")
    
    for i, (cmd, state) in enumerate(st.session_state.repo.history):
        h_col1, h_col2, h_col3, h_col4 = st.columns([1, 4, 1, 1])
        
        with h_col1:
            st.markdown(f"**{i+1}**")
        
        with h_col2:
            st.code(cmd)
        
        with h_col3:
            if st.button("↶", key=f"revert_{i}", help=f"Reset to step {i+1}"):
                if st.session_state.repo.reset_to_step(i):
                    st.success(f"Reset to step {i+1}")
                    st.rerun()
        
        with h_col4:
            # Show number of commits at this step
            num_commits = len(state.commits)
            st.markdown(f"{num_commits} commits")

# ============================================================================
# EXPLANATION PANEL
# ============================================================================

if st.session_state.repo.history:
    st.markdown("---")
    st.markdown("### 📚 Command Explanation")
    
    last_cmd = st.session_state.repo.history[-1][0]
    explanation = _get_command_explanation(last_cmd)
    
    st.info(explanation)
else:
    st.markdown("---")
    st.info("💡 Execute a command to see its explanation here.")

# ============================================================================
# LEGEND
# ============================================================================

st.markdown("---")
st.markdown("### 🔑 Legend")

leg_col1, leg_col2, leg_col3 = st.columns(3)

with leg_col1:
    st.markdown("""
    **Commit Visualization**
    - ◆ Current commit (gold)
    - ● Other commits (blue)
    """)

with leg_col2:
    st.markdown("""
    **References**
    - 🟢 Branch pointer
    - 🔴 HEAD pointer
    """)

with leg_col3:
    st.markdown("""
    **File State**
    - ✓ Staged files
    - ~ Modified files
    - + New files
    - – Deleted files
    """)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_command_explanation(command: str) -> str:
    """Get educational explanation for a Git command."""
    
    explanations = {
        "git init": "**git init** creates a new Git repository. It initializes the `.git` directory and creates the default `main` branch.",
        
        "git add": "**git add** stages changes for commit. Files in the staging area will be included in the next commit.",
        
        "git commit": "**git commit** creates a new snapshot (commit) of your staged changes. Each commit has a unique SHA identifier and a parent commit.",
        
        "git branch": "**git branch** creates a new branch. A branch is just a pointer to a commit, allowing you to work on multiple features simultaneously.",
        
        "git switch": "**git switch** moves HEAD to a different branch. This updates your working directory to match the commit pointed to by that branch.",
        
        "git checkout": "**git checkout** is a legacy command that does the same thing as git switch.",
        
        "git merge": "**git merge** combines commits from another branch into the current branch. If the target branch contains commits not in the current branch, a merge commit is created.",
        
        "git rebase": "**git rebase** replays your branch commits on top of another base, creating new commit identities.",
        
        "git cherry-pick": "**git cherry-pick** applies the changes introduced by an existing commit as a new commit on the current branch.",
        
        "git reset": "**git reset** moves the current branch pointer to a different commit. Different modes affect the staging area and working directory differently.",
        
        "git restore": "**git restore** discards changes in the working directory or unstages files without moving branch pointers.",
        
        "git log": "**git log** displays the commit history. Add `--oneline` for a compact view.",
        
        "git status": "**git status** shows the current state: which branch you're on, staged changes, and modifications.",
        
        "git reflog": "**git reflog** shows the reference logs - a record of all HEAD movements. Useful for recovering lost commits!",
        
        "git detach": "**Detached HEAD** means HEAD points directly to a commit instead of a branch. New commits are not advanced through a branch pointer.",
        "git remote": "**git remote** names a remote repository. In this simulator, the remote is an in-memory teaching model.",
        "git push": "**git push** sends the current local branch pointer to the simulated remote. The remote branch moves, while your local branch remains where it was.",
        "git fetch": "**git fetch** refreshes local remote-tracking references without changing your current branch.",
        "git pull": "**git pull** fetches the remote and then fast-forwards the current branch when the histories are compatible.",
        "git stash": "**git stash** saves working-tree and staged changes away so you can return to a clean working tree. Apply or pop the stash later to restore the work.",
        "git tag": "**git tag** creates a stable name for a commit. Lightweight tags are simple pointers; annotated tags also carry a message in this simulator.",
    }
    
    for cmd_pattern, explanation in explanations.items():
        if cmd_pattern in command:
            return explanation
    
    return "Execute a Git command to learn what it does! 🚀"
