# Title of the PR changeset (Fix certain issue, or Implement/Add feature)

Adds feature to import group structure from rhino file and link objects

## detailed explanation
* collects all group ids from rhino objects and creates the according collections in Blender
* has option to recreate nested group hierarchy as collections instead of importing all groups in parallel
* tested for named and unnamed objects, nested and simple groups, reimporting the same file and reimporting over a previously ungrouped file
* possible issue that needs to be adressed: since the r3d group ids are simple integers and dont carry a uuid they are not unique and will create unpredictable behaviour when importing another file with same group names

## fixes / resolves
Fixes #7
