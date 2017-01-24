# Devstack extras script to install Karbor

# Test if any karbor services are enabled
# is_karbor_enabled
function is_karbor_enabled {
    echo "Checking if Karbor is Enabled"
    [[ ,${ENABLED_SERVICES} =~ ,"karbor-" ]] &&  Q_ENABLE_KARBOR="False"
    Q_ENABLE_KARBOR="True"
}

function _create_karbor_conf_dir {

    # Put config files in ``KARBOR_CONF_DIR`` for everyone to find

    sudo install -d -o $STACK_USER $KARBOR_CONF_DIR

}

# create_karbor_accounts() - Set up common required karbor accounts
# Tenant               User       Roles
# ------------------------------------------------------------------
# service              karbor      service
function create_karbor_accounts {

    if is_service_enabled karbor-api; then

        create_service_user "$KARBOR_SERVICE_NAME" "admin"

        get_or_create_service "$KARBOR_SERVICE_NAME" "$KARBOR_SERVICE_TYPE" "Application Data Protection Service"
        get_or_create_endpoint "$KARBOR_SERVICE_TYPE" "$REGION_NAME" \
            "$KARBOR_API_PROTOCOL://$KARBOR_API_HOST:$KARBOR_API_PORT/v1/\$(project_id)s" \
            "$KARBOR_API_PROTOCOL://$KARBOR_API_HOST:$KARBOR_API_PORT/v1/\$(project_id)s" \
            "$KARBOR_API_PROTOCOL://$KARBOR_API_HOST:$KARBOR_API_PORT/v1/\$(project_id)s"
    fi
}

function configure_karbor_api {
    if is_service_enabled karbor-api ; then
        echo "Configuring Karbor API"

        cp $KARBOR_DIR/etc/karbor.conf $KARBOR_API_CONF
        cp $KARBOR_DIR/etc/api-paste.ini $KARBOR_CONF_DIR
        cp $KARBOR_DIR/etc/policy.json $KARBOR_CONF_DIR
        cp -R $KARBOR_DIR/etc/providers.d $KARBOR_CONF_DIR

        iniset $KARBOR_API_CONF DEFAULT debug $ENABLE_DEBUG_LOG_LEVEL
        iniset $KARBOR_API_CONF DEFAULT use_syslog $SYSLOG
        iniset $KARBOR_API_CONF DEFAULT min_interval 900
        iniset $KARBOR_API_CONF DEFAULT min_window_time 225
        iniset $KARBOR_API_CONF DEFAULT max_window_time 450
        echo "Configuring Karbor API Database"
        iniset $KARBOR_API_CONF database connection `database_connection_url karbor`
        iniset_rpc_backend karbor $KARBOR_API_CONF

        setup_colorized_logging $KARBOR_API_CONF DEFAULT
        echo "Configuring Karbor API colorized"
        if is_service_enabled keystone; then

            echo "Configuring Karbor keystone Auth"
            create_karbor_cache_dir

            # Configure auth token middleware
            configure_auth_token_middleware $KARBOR_API_CONF karbor \
                $KARBOR_AUTH_CACHE_DIR

            # Configure for trustee
            iniset $KARBOR_API_CONF trustee auth_type password
            iniset $KARBOR_API_CONF trustee auth_url $KEYSTONE_AUTH_URI
            iniset $KARBOR_API_CONF trustee username karbor
            iniset $KARBOR_API_CONF trustee password $SERVICE_PASSWORD
            iniset $KARBOR_API_CONF trustee user_domain_id default

            # Configure for clients_keystone
            iniset $KARBOR_API_CONF clients_keystone auth_uri $KEYSTONE_AUTH_URI

            # Config karbor client
            iniset $KARBOR_API_CONF karbor_client service_name $KARBOR_SERVICE_NAME
            iniset $KARBOR_API_CONF karbor_client service_type $KARBOR_SERVICE_TYPE
            iniset $KARBOR_API_CONF karbor_client version 1

        else
            iniset $KARBOR_API_CONF DEFAULT auth_strategy noauth
        fi
    fi
}

function create_karbor_cache_dir {

    # Delete existing dir
    sudo rm -rf $KARBOR_AUTH_CACHE_DIR
    sudo mkdir -p $KARBOR_AUTH_CACHE_DIR
    sudo chown `whoami` $KARBOR_AUTH_CACHE_DIR

}

is_karbor_enabled

if [[ "$Q_ENABLE_KARBOR" == "True" ]]; then
    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        echo summary "Karbor pre-install"
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing Karbor"

        setup_package $KARBOR_DIR -e
        _create_karbor_conf_dir

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring Karbor"

        configure_karbor_api

        echo export PYTHONPATH=\$PYTHONPATH:$KARBOR_DIR >> $RC_DIR/.localrc.auto

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then

        echo_summary "Creating Karbor entities for auth service"
        create_karbor_accounts

        echo_summary "Initializing Karbor Service"
        KARBOR_BIN_DIR=$(get_python_exec_prefix)

        if is_service_enabled $DATABASE_BACKENDS; then
            # (re)create karbor database
            recreate_database karbor utf8

            # Migrate karbor database
            $KARBOR_BIN_DIR/karbor-manage db sync
        fi
        if is_service_enabled karbor-api; then
            run_process karbor-api "$KARBOR_BIN_DIR/karbor-api --config-file $KARBOR_API_CONF"
        fi
        if is_service_enabled karbor-operationengine; then
           run_process karbor-operationengine "$KARBOR_BIN_DIR/karbor-operationengine --config-file $KARBOR_API_CONF"
        fi
        if is_service_enabled karbor-protection; then
           run_process karbor-protection "$KARBOR_BIN_DIR/karbor-protection --config-file $KARBOR_API_CONF"
        fi
    fi

    if [[ "$1" == "unstack" ]]; then

        if is_service_enabled karbor-api; then
           stop_process karbor-api
        fi
        if is_service_enabled karbor-operationengine; then
           stop_process karbor-operationengine
        fi
        if is_service_enabled karbor-protection; then
           stop_process karbor-protection
        fi
    fi
fi
