#!/data/data/com.termux/files/usr/bin/bash

REPO_DIR="/data/data/com.termux/files/home/chris/boutique"
DB_PATH="$REPO_DIR/Databases/boutique.db"
DB_BACKUP="$REPO_DIR/Databases/boutique.db.backup"

cd "$REPO_DIR" || { echo "❌ Error: Cannot access $REPO_DIR"; exit 1; }

# Ensure it's a Git repo
git rev-parse --is-inside-work-tree > /dev/null 2>&1 || { echo "❌ Not a Git repository"; exit 1; }

# Backup the database
if [ -f "$DB_PATH" ]; then
    cp "$DB_PATH" "$DB_BACKUP"
    echo "✅ Backed up DB to $DB_BACKUP"
fi

# Add and commit local changes
git add Databases static
git commit -m "Auto: push DB and static updates" || echo "No changes to commit."

# Push changes before pulling
git push origin "$(git rev-parse --abbrev-ref HEAD)"

# Stash any other local changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "📦 Stashing local changes"
    git stash push -m "Pre-pull stash"
fi

# Pull with theirs strategy for binary (use theirs = prefer remote)
echo "⬇️ Pulling updates (ours wins on conflict for binary)..."
GIT_MERGE_AUTOEDIT=no git pull --strategy=recursive -X ours origin "$(git rev-parse --abbrev-ref HEAD)"

# Restore DB from backup if needed
if [ ! -f "$DB_PATH" ] && [ -f "$DB_BACKUP" ]; then
    cp "$DB_BACKUP" "$DB_PATH"
    echo "🔁 Restored missing DB file from backup."
fi

# Try popping the stash
if git stash list | grep -q "Pre-pull stash"; then
    git stash pop || echo "⚠️ Could not reapply stashed changes cleanly"
fi

echo "✅ Done: DB is pushed, pull complete, and conflicts avoided."
