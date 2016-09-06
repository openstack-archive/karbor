# Karbor API #

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
{
  "plans": [
    {
      "id": "9e5475d2-6425-4986-9136-a4f09642297f",
      "name": "My 3 tier application",
      "resources": [
        {
          "type": "OS::Nova::Server",
          "id": "6888e66d-f63c-44f5-b3e5-7c96049d3c54",
          "name": "App server"
        },
        {
          "type": "OS::Cinder::Volume",
          "id": "c8e6017d-6abc-4357-8c42-390f37984967",
          "name": "System volume"
        },
        {
          "type": "OS::Cinder::Volume",
          "id": "0041a63a-7c71-4410-adfe-999fc8287d58",
          "name": "Data volume"
        }
      ],
      "status": "suspended",
      "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
      "parameters": {
        "OS::Nova::Server": {
          "backup_name": "os"
        },
        "OS::Nova::Server#64e51e85-4f31-441f-9a5d-6e93e3193312": {
          "backup_name": "crash"
        },
        "OS::Cinder::Volume": {
          "backup_name": "os"
        },
        "OS::Cinder::Volume#61e51e85-4f31-441f-9a5d-6e93e3196628": {
          "backup_name": "crash"
        }
      }
    }
  ],
  "plans_links": [
    {
      "href": "/v1/{project_id}/plans?limit={limit_num}&marker=9e5475d2-6425-4986-9136-a4f09642297f",
      "rel": "next"
    }
  ]
}
```

### Create Plan ###
> **post** : /v1/{project_id}/plans
#### Request JSON ####
```json
{
  "plan": {
    "name": "My 3 tier application",
    "resources": [
      {
        "type": "OS::Nova::Server",
        "id": "6888e66d-f63c-44f5-b3e5-7c96049d3c54",
        "name": "App server"
      },
      {
        "type": "OS::Cinder::Volume",
        "id": "c8e6017d-6abc-4357-8c42-390f37984967",
        "name": "System volume"
      },
      {
        "type": "OS::Cinder::Volume",
        "id": "0041a63a-7c71-4410-adfe-999fc8287d58",
        "name": "Data volume"
      }
    ],
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "parameters": {
      "OS::Nova::Server": {
        "backup_name": "os"
      },
      "OS::Nova::Server#64e51e85-4f31-441f-9a5d-6e93e3193312": {
        "backup_name": "crash"
      },
      "OS::Cinder::Volume": {
        "backup_name": "os"
      },
      "OS::Cinder::Volume#61e51e85-4f31-441f-9a5d-6e93e3196628": {
        "backup_name": "crash"
      }
    }
  }
}
```

#### Response JSON ####
```json
{
  "plan": {
    "id": "9e5475d2-6425-4986-9136-a4f09642297f",
    "name": "My 3 tier application",
    "resources": [
      {
        "type": "OS::Nova::Server",
        "id": "6888e66d-f63c-44f5-b3e5-7c96049d3c54",
        "name": "App server"
      },
      {
        "type": "OS::Cinder::Volume",
        "id": "c8e6017d-6abc-4357-8c42-390f37984967",
        "name": "System volume"
      },
      {
        "type": "OS::Cinder::Volume",
        "id": "0041a63a-7c71-4410-adfe-999fc8287d58",
        "name": "Data volume"
      }
    ],
    "status": "suspended",
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "parameters": {
      "OS::Nova::Server": {
        "backup_name": "os"
      },
      "OS::Nova::Server#64e51e85-4f31-441f-9a5d-6e93e3193312": {
        "backup_name": "crash"
      },
      "OS::Cinder::Volume": {
        "backup_name": "os"
      },
      "OS::Cinder::Volume#61e51e85-4f31-441f-9a5d-6e93e3196628": {
        "backup_name": "crash"
      }
    }
  }
}
```

### Show Plan ###
> **get** : /v1/{project_id}/plans/{plan_id}
#### Response JSON ####
```json
{
  "plan": {
    "id": "9e5475d2-6425-4986-9136-a4f09642297f",
    "name": "My 3 tier application",
    "resources": [
      {
        "type": "OS::Nova::Server",
        "id": "6888e66d-f63c-44f5-b3e5-7c96049d3c54",
        "name": "App server"
      },
      {
        "type": "OS::Cinder::Volume",
        "id": "c8e6017d-6abc-4357-8c42-390f37984967",
        "name": "System volume"
      },
      {
        "type": "OS::Cinder::Volume",
        "id": "0041a63a-7c71-4410-adfe-999fc8287d58",
        "name": "Data volume"
      }
    ],
    "status": "suspended",
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "parameters": {
      "OS::Nova::Server": {
        "backup_name": "os"
      },
      "OS::Nova::Server#64e51e85-4f31-441f-9a5d-6e93e3193312": {
        "backup_name": "crash"
      },
      "OS::Cinder::Volume": {
        "backup_name": "os"
      },
      "OS::Cinder::Volume#61e51e85-4f31-441f-9a5d-6e93e3196628": {
        "backup_name": "crash"
      }
    }
  }
}
```

### Update Plan ###
> **put** : /v1/{project_id}/plans/{plan_id}
#### Request JSON ####
```json
{
  "plan":{
    "status": "started",
    "name": "My 1 tier application"
  }
}
```

#### Response JSON ####
```json
{
  "plan": {
    "id": "9e5475d2-6425-4986-9136-a4f09642297f",
    "name": "My 1 tier application",
    "resources": [
      {
        "type": "OS::Nova::Server",
        "id": "6888e66d-f63c-44f5-b3e5-7c96049d3c54",
        "name": "App server"
      },
      {
        "type": "OS::Cinder::Volume",
        "id": "c8e6017d-6abc-4357-8c42-390f37984967",
        "name": "System volume"
      },
      {
        "type": "OS::Cinder::Volume",
        "id": "0041a63a-7c71-4410-adfe-999fc8287d58",
        "name": "Data volume"
      }
    ],
    "status": "started",
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "parameters": {
      "OS::Nova::Server": {
        "backup_name": "os"
      },
      "OS::Nova::Server#64e51e85-4f31-441f-9a5d-6e93e3193312": {
        "backup_name": "crash"
      },
      "OS::Cinder::Volume": {
        "backup_name": "os"
      },
      "OS::Cinder::Volume#61e51e85-4f31-441f-9a5d-6e93e3196628": {
        "backup_name": "crash"
      }
    }
  }
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
{"operations": [
    {"scheduled_operation": {
       "id": "1a2c0c3d-f402-4cd8-b5db-82e85cb51fad",
       "name": "My scheduled operation",
       "description": "It will run everyday",
       "operation_type": "protect",
       "trigger_id": "23902b02-5666-4ee6-8dfe-962ac09c3995",
       "operation_definition": {
         "provider_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa399",
         "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
         },
       "enabled": 1
      }
    },
  ],
  "operations_links": ""
}
```

### Create Scheduled Operation ###
> **post** : /v1/{project_id}/scheduled_operations
#### Request JSON ####
```json
{"scheduled_operation": {
    "name": "My scheduled operation",
    "description": "It will run everyday",
    "operation_type": "protect",
    "trigger_id": "23902b02-5666-4ee6-8dfe-962ac09c3995",
    "operation_definition": {
      "provider_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa399",
      "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
    }
  }
}
```

#### Response JSON ####
```json
{"scheduled_operation": {
    "id": "1a2c0c3d-f402-4cd8-b5db-82e85cb51fad",
    "name": "My scheduled operation",
    "description": "It will run everyday",
    "operation_type": "protect",
    "trigger_id": "23902b02-5666-4ee6-8dfe-962ac09c3995",
    "operation_definition": {
      "provider_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa399",
      "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
    },
    "enabled": 1
  }
}
```

### Show Scheduled Operation ###
> **get** : /v1/{project_id}/scheduled_operations/{scheduled_operation_id}
#### Response JSON ####
```json
{"scheduled_operation": {
    "id": "1a2c0c3d-f402-4cd8-b5db-82e85cb51fad",
    "name": "My scheduled operation",
    "description": "It will run everyday",
    "operation_type": "protect",
    "trigger_id": "23902b02-5666-4ee6-8dfe-962ac09c3995",
    "operation_definition": {
      "provider_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa399",
      "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
    },
    "enabled": 1
  }
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
{"triggers": [
    {"trigger_info": {
      "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
      "name": "My backup trigger",
      "type": "time",
      "properties": {
        "format": "crontab",
        "pattern": "0 9 * * *",
        "start_time": "2015-12-17T08:30:00",
        "end_time": "2016-03-17T08:30:00",
        "window": "3600",
        }
      }
    },
  ],
 "triggers_links": ""  
}
```

### Create Trigger ###
> **post** : /v1/{project_id}/triggers
#### Request JSON ####
```json
{"trigger_info": {
   "name": "My backup trigger",
   "type": "time",
   "properties": {
     "format": "crontab",
     "pattern": "0 9 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
    }
  }
}
```

#### Response JSON ####
```json
{"trigger_info": {
   "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
   "name": "My backup trigger",
   "type": "time",
   "properties": {
     "format": "crontab",
     "pattern": "0 9 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
    }
  }
}
```

### Update Trigger ###
> **post** : /v1/{project_id}/triggers/{trigger_id}
#### Request JSON ####
```json
{"trigger_info": {
   "properties": {
     "format": "crontab",
     "pattern": "0 10 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
    }
  }
}
```

#### Response JSON ####
```json
{"trigger_info": {
   "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
   "name": "My backup trigger",
   "type": "time",
   "properties": {
     "format": "crontab",
     "pattern": "0 10 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
    }
  }
}
```

### Show Trigger ###
> **get** : /v1/{project_id}/triggers/{trigger_id}
#### Response JSON ####
```json
{"trigger_info": {
   "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
   "name": "My backup trigger",
   "type": "time",
   "properties": {
     "format": "crontab",
     "pattern": "0 9 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
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
