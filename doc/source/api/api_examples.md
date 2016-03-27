# Smaug API #

----------

## Protection Provider ##

### List Protection Providers ###

> **get** : /v1/providers

#### Response JSON ####
```json
[
  {
    "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
    "name": "OS Infra Provider",
    "description": "This provider uses OpenStack's own services (swift, cinder) as storage"
  },
]
```

### Show Protection Provider ###
> **get** : /v1/providers/{provider_id}
#### Response JSON ####
```json
{
    "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
    "name": "OS Infra Provider",
    "description": "This provider uses OpenStack's own services (swift, cinder) as storage",  "saved_info_schema": {
        "OS::Cinder::Volume": {
            "title": "Nova Server Info Schema",
            "type": "object",
            "properties": {
                "backup_id": {
                    "type": "string",
                    "title": "Backup ID",
                    "description": "The backup volume id"
                }
            }
        }
    },
    "options_schema": {
        "OS::Nova::Server": {
            "title": "Nova Server Backup Options",
            "type": "object",
            "properties": {
                "consistency": {
                    "enum": ["crash", "os", "application"],
                    "title": "Consistency Level",
                    "description": "The desired consistency level required"
                }
            }
        }
    },
    "restore_schema": {
        "OS::Nova::Server": {
            "title": "Nova Server Restore Options",
            "type": "object",
            "properties": {
                "public_ip": {
                    "title": "Replacement public IP",
                    "type": "string",
                    "description": "The public IP to use on the restore site for the VM"
                }
            }
        }
    }
}
```

----------

## Checkpoint ##

### List Checkpoints ###
> **get** : /v1/providers/{provider_id}/checkpoints
#### Response JSON ####
```json
[
  {
    "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
    "project_id": "446a04d8-6ff5-4e0e-99a4-827a6389e9ff",
    "status": "committed",
    "plan": {
        "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
        "name": "My 3 tier application",
        "description": "The protection plan for my application"
    },
    "provider_id":  "efc6a88b-9096-4bb6-8634-cda182a6e12a"
  },
]
```

### Create Checkpoint ###
> **post** : /v1/providers/{provider_id}/checkpoints
#### Response JSON ####
```json
{
  "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
  "project_id": "446a04d8-6ff5-4e0e-99a4-827a6389e9ff",
  "status": "committed",
  "plan": {
    "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
  },
  "provider_id": "efc6a88b-9096-4bb6-8634-cda182a6e12a"
}
```

### Show Checkpoint ###
> **get** : /v1/providers/{provider_id}/checkpoints/{checkpoint_id}
#### Response JSON ####
```json
{
  "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
  "project_id": "446a04d8-6ff5-4e0e-99a4-827a6389e9ff",
  "status": "committed",
  "plan": {
      "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
      "name": "My 3 tier application",
      "description": "The protection plan for my application"
  },
  "provider_id": "efc6a88b-9096-4bb6-8634-cda182a6e12a"
}
```

### Delete Checkpoint ###
> **delete** : /v1/providers/{provider_id}/checkpoints/{checkpoint_id}
#### Response JSON ####
```json
None
```

----------

## Plan ##

### List Plans ###
> **get** : /v1/{project_id}/plans
#### Response JSON ####
```json
[
  {
    "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
    "name": "My 3 tier application",
    "description": "The protection plan for my application"
  },
]
```

### Create Plan ###
> **post** : /v1/{project_id}/plans
#### Response JSON ####
```json
{
  "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
  "name": "My 3 tier application",
  "resources": [
    {
      "id": "64e51e85-4f31-441f-9a5d-6e93e3196628",
      "type": "OS::Nova::Server"
    },
    {
      "id": "61e51e85-4f31-441f-9a5d-6e93e3196628",
      "type": "OS::Cinder::Volume"
    },
    {
      "id": "62e51e85-4f31-441f-9a5d-6e93e3196628",
      "type": "OS::Cinder::Volume"
    }
  ],
  "parameters": {
    "OS::Nova::Server": {
      "consistency": "os"
    }
  },
  "provider_id": "efc6a88b-9096-4bb6-8634-cda182a6e12a"
}
```

### Show Plan ###
> **get** : /v1/{project_id}/plans/{plan_id}
#### Response JSON ####
```json
{
  "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
  "name": "My 3 tier application",
  "resources": [
    {
      "id": "64e51e85-4f31-441f-9a5d-6e93e3196628",
      "type": "OS::Nova::Server"
    },
    {
      "id": "61e51e85-4f31-441f-9a5d-6e93e3196628",
      "type": "OS::Cinder::Volume"
    },
    {
      "id": "62e51e85-4f31-441f-9a5d-6e93e3196628",
      "type": "OS::Cinder::Volume"
    }
  ],
  "parameters": {
    "OS::Nova::Server": {
      "consistency": "crash"
    }
  },
  "provider_id": "efc6a88b-9096-4bb6-8634-cda182a6e12a"
}
```

### Delete Plan ###
> **delete** : /v1/{project_id}/plans/{plan_id}
#### Response JSON ####
```json
None
```

----------

## Protectable ##

### List Protectable Types ###
> **get** : /v1/protectables
#### Response JSON ####
```json
[
  "OS::Nova::Server",
  "OS::Cinder::Volume"
]
```

### Show Protectable Type ###
> **get** : /v1/protectables/{protectable_type}
#### Response JSON ####
```json
{
  "name": "OS::Nova::Server",
  "dependent_types": [
    "OS::Cinder::Volume",
    "OS::Glance::Image",
  ]
}
```

### List Protectable Instances ###
> **get** : /v1/protectables/{protectable_type}/instances
#### Response JSON ####
```json
[
  {
    "id": "557d0cd2-fd8d-4279-91a5-24763ebc6cbc",
    "type": "OS::Nova::Server",
    "dependent_resources": [
      {
        "id": "5fad94de-2926-486b-ae73-ff5d3477f80d",
        "type": "OS::Cinder::Volume"
      }
    ]
  },
]
```

----------

## Scheduled Operation ##

### List Scheduled Operations ###
> **get** : /v1/{project_id}/scheduled_operations
#### Response JSON ####
```json
[
  {
    "id": "1a2c0c3d-f402-4cd8-b5db-82e85cb51fad",
    "name": "My scheduled operation",
    "project_id": "23902b02-5666-4ee6-8dfe-962ac09c3994",
    "operation_type": "protect",
    "operation_definition": {
      "trigger_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
      "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
    }
  },
]
```

### Create Scheduled Operation ###
> **post** : /v1/{project_id}/scheduled_operations
#### Request JSON ####
```json
{
  "name": "My scheduled operation",
  "project_id": "23902b02-5666-4ee6-8dfe-962ac09c3994",
  "operation_type": "protect",
  "operation_definition": {
    "trigger_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
    "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
  }
}
```

#### Response JSON ####
```json
{
  "id": "1a2c0c3d-f402-4cd8-b5db-82e85cb51fad",
  "name": "My scheduled operation",
  "project_id": "23902b02-5666-4ee6-8dfe-962ac09c3994",
  "operation_type": "protect",
  "operation_definition": {
    "trigger_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
    "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
  }
}
```

### Show Scheduled Operation ###
> **get** : /v1/{project_id}/scheduled_operations/{scheduled_operation_id}
#### Response JSON ####
```json
{
  "id": "1a2c0c3d-f402-4cd8-b5db-82e85cb51fad",
  "name": "My scheduled operation",
  "project_id": "23902b02-5666-4ee6-8dfe-962ac09c3994",
  "operation_type": "protect",
  "operation_definition": {
    "trigger_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
    "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
  },
  "next_schedule_time": "2016-1-5T08:30:00"
}
```

### Delete Scheduled Operation ###
> **delete** : /v1/{project_id}/scheduled_operations/{scheduled_operation_id}
#### Response JSON ####
```json
None
```

----------

## Restores ##

### List Restores ###
> **get** : /v1/{project_id}/restores
#### Response JSON ####
```json
[
  {
	"id": "36ea41b2-c358-48a7-9117-70cb7617410a",
	"project_id": "586cc6ce-e286-40bd-b2b5-dd32694d9944",
	"provider_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
	"checkpoint_id": "09edcbdc-d1c2-49c1-a212-122627b20968",
	"restore_target": "192.168.1.2:35357/v2.0",
	"parameters": {
	  "username": "admin"
	},
	"status": "SUCCESS"
  },
]
```

### Create Restore ###
> **post** : /v1/{project_id}/restores
#### Response JSON ####
```json
{
  "id": "36ea41b2-c358-48a7-9117-70cb7617410a",
  "project_id": "586cc6ce-e286-40bd-b2b5-dd32694d9944",
  "provider_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
  "checkpoint_id": "09edcbdc-d1c2-49c1-a212-122627b20968",
  "restore_target": "192.168.1.2:35357/v2.0",
  "parameters": {
    "username": "admin"
  },
  "status": "IN PROGRESS"
}
```

### Show Restore ###
> **get** : /v1/{project_id}/restores/{restore_id}
#### Response JSON ####
```json
{
  "id": "36ea41b2-c358-48a7-9117-70cb7617410a",
  "project_id": "586cc6ce-e286-40bd-b2b5-dd32694d9944",
  "provider_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
  "checkpoint_id": "09edcbdc-d1c2-49c1-a212-122627b20968",
  "restore_target": "192.168.1.2:35357/v2.0",
  "parameters": {
    "username": "admin"
  },
  "status": "IN PROGRESS"
}
```

----------

## Trigger ##

### List Triggers ###
> **get** : /v1/{project_id}/triggers
#### Response JSON ####
```json
[
  {
    "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
    "name": "My backup trigger",
    "type": "TimeTrigger",
    "description": "The time trigger for backup weekly"
  },
]
```

### Create Trigger ###
> **post** : /v1/{project_id}/triggers
#### Response JSON ####
```json
{
  "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
  "name": "My backup trigger",
  "type": "TimeTrigger",
  "properties": {
    "trigger_window": "60",
    "recurrence": {
      "start": "2015-12-17T08:30:00",
      "frequency": "weekly"
    }
  }
}
```

### Show Trigger ###
> **get** : /v1/{project_id}/triggers/{trigger_id}
#### Response JSON ####
```json
{
  "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
  "name": "My backup trigger",
  "type": "TimeTrigger",
  "properties": {
    "trigger_window": "60",
    "recurrence": {
      "start": "2015-12-17T08:30:00",
      "frequency": "weekly"
    }
  }
}
```

### Delete Trigger ###
> **delete** : /v1/{project_id}/triggers/{trigger_id}
#### Response JSON ####
```json
None
```
