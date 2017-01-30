# Bank basics

*** :exclamation: This is still a work in progress ***

This document will describe the layout and algorithms used by Karbor using the
default bank implementation. Providers can use their own algorithms to manage
metadata but there might be issues when using default plugins.

## Abstract

Since Karbor wants to be able to store metadata in many locations (swift, mongodb, etc.)
we defined a simplified object store interface that we believe most backends will be able
to support without much work.

But the simplified interface doesn't describe how Karbor will do it's higher
level operations and how the higher level logic will be laid out in the object
store. This is why we need higher level logic defined explicitly so that later
we could use higher level bank functions knowing they are correct, safe and atomic.

## Layout

### Checkpoint directory

`/checkpoints/<checkpoint_id>/index.json`

#### Example content
*time is in ISO 8601 time UTC*
```json
{
    "trigger": {},
    "started_at": "2015-10-29T13:41:02Z",
    "status": "in progress",
    "plan": {},
    "provider_id": "bc9f8572-6908-4353-aed5-2ba165c78aa6",
    "provider_version": "1.2.0",
    "plugins": {
        "plugin_1": {
            "name": "cinder volume",
            "version": "1.2.3",
        }
    }
}
```

### Protection definition directory

`/checkpoints/<checkpoint_id>/<resource_id>/index.json`

#### Example content

```json
{
    "name": "vm",
    "id": "8a562ed6-81ff-4bda-9672-2a8c49f130c3",
    "dependent_resources": [
        "92b022d9-cca4-4d02-b7fb-6cec9183d9f2",
        "b081d472-023c-4a98-b57b-f2013996739b"
    ]
}
```

### Protection definition plugin data directory

`/checkpoints/<checkpoint_id>/<resource_id>/plugin_data/*`

## Checkpoint Creation Process

Create new Checkpoint with id <CHECKPOINT-ID>;

1. Acquire checkpoint lease
 * action acquire_lease
 * id: `<CHECKPOINT-ID>`
2. Create checkpoint pointer
 * action: write_object
 * path: `/indices/unfinished_checkpoints/<CHECKPOINT-ID>`,
 * buffer: `<CHECKPOINT-ID>`
3. Create checkpoint
 * action: write_object
 * path: `/checkpoints/<CHECKPOINT-ID>/index.json`,
 * buffer:
   ```json
   {
       "karbor_version": "1.0.0",
       "status": "in_progress",
       "plugins": {}
   }
   ```
4. Run plugins
5. Checkpoint finished but indices not yet created
 * action: write_object
 * path: `/checkpoints/<CHECKPOINT-ID>/index.json`,
 * buffer:
   ```json
   {
       "karbor_version": "1.0.0",
       "status": "creating_indices",
       "plugins": {}
   }
   ```
6. Create index 'plan' (Example, there could be any number of indexes)
  * action: write_object
  * path: `/indices/by_plan/<PLAN-ID>/<CHECKPOINT-ID>`
  * buffer: `<CHECKPOINT-ID>`
7. Remove checkpoint pointer
  * action: delete_object
  * path: `/indices/unfinished_checkpoints/<CHECKPOINT-ID>`
8. Release checkpoint lease
  * action: release_lease
  * id: `<CHECKPOINT-ID>`

## Delete Checkpoint

1. Create checkpoint pointer
 * action: write_object
 * path: `/indices/deleted_checkpoints/<CHECKPOINT-ID>`,
 * buffer: `<CHECKPOINT-ID>`
2. Mark transaction as being deleted
 * action: write_object
 * path: `/checkpoints/<CHECKPOINT-ID>/index.json`,
 * buffer:
   ```json
   {
       "karbor_version": "1.0.0",
       "status": "deleting",
       "plugins": {}
   }
   ```
From this point on the checkpoint is considered deleted and should not be used
or returned by the provider.

## GC

When deleting a checkpoint the checkpoint is only marked as deleted. On of the
Karbor server will have to run a GC collection run and make sure all the actual
data is free. This is done to unify all the cleanup to one flow and make sure
the deletion has been propagated to all sites before actually deleting the data.


For each checkpoint in `/indices/deleted_checkpoints`

1. Remove indices
  - Remove index 'plan' (Example, there could be any number of indexes)
    * action: delete_object
    * path: `/indices/by_plan/<PLAN-ID>/<CHECKPOINT-ID>`
2. Run plugins
3. Delete checkpoint file
 * action: delete_object
 * path: `/checkpoints/<CHECKPOINT-ID>/index.json`,
4. Remove checkpoints pointer
  * action: delete_object
  * path: `/indices/unfinished_checkpoints/<CHECKPOINT-ID>`
5. Delete checkpoint deletion marker
   * action: delete_object
   * path: `/indices/deleted_checkpoints/<CHECKPOINT-ID>`
