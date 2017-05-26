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
            "$KARBOR_API_ENDPOINT" \
            "$KARBOR_API_ENDPOINT" \
            "$KARBOR_API_ENDPOINT"
    fi
}


# karbor_config_apache_wsgi() - Set WSGI config files
function karbor_config_apache_wsgi {
    local karbor_apache_conf
    karbor_apache_conf=$(apache_site_config_for osapi_karbor)
    local karbor_ssl=""
    local karbor_certfile=""
    local karbor_keyfile=""
    local karbor_api_port=$KARBOR_API_PORT

    if is_ssl_enabled_service karbor-api; then
        karbor_ssl="SSLEngine On"
        karbor_certfile="SSLCertificateFile $KARBOR_SSL_CERT"
        karbor_keyfile="SSLCertificateKeyFile $KARBOR_SSL_KEY"
    fi

    # copy proxy vhost file
    sudo cp $KARBOR_API_APACHE_TEMPLATE $karbor_apache_conf
    sudo sed -e "
        s|%PUBLICPORT%|$karbor_api_port|g;
        s|%APACHE_NAME%|$APACHE_NAME|g;
        s|%APIWORKERS%|$API_WORKERS|g
        s|%KARBOR_BIN_DIR%|$KARBOR_BIN_DIR|g;
        s|%SSLENGINE%|$karbor_ssl|g;
        s|%SSLCERTFILE%|$karbor_certfile|g;
        s|%SSLKEYFILE%|$karbor_keyfile|g;
        s|%USER%|$STACK_USER|g;
    " -i $karbor_apache_conf
}

function karbor_config_uwsgi {
    write_uwsgi_config "$KARBOR_API_UWSGI_CONF" "$KARBOR_API_UWSGI" "/$KARBOR_SERVICE_TYPE"
}

# clean_karbor_api_mod_wsgi() - Remove wsgi files, disable and remove apache vhost file
function clean_karbor_api_mod_wsgi {
    sudo rm -f $(apache_site_config_for osapi_karbor)
}

function clean_karbor_api_uwsgi {
    remove_uwsgi_config "$KARBOR_API_UWSGI_CONF" "$KARBOR_API_UWSGI"
}

# start_karbor_api_mod_wsgi() - Start the API processes ahead of other things
function start_karbor_api_mod_wsgi {
    enable_apache_site osapi_karbor
    restart_apache_server
    tail_log karbor-api /var/log/$APACHE_NAME/karbor-api.log

    echo "Waiting for Karbor API to start..."
    if ! wait_for_service $SERVICE_TIMEOUT $KARBOR_API_ENDPOINT; then
        die $LINENO "karbor-api mod_wsgi did not start"
    fi
}

function start_karbor_api_uwsgi {
    run_process karbor-api "$KARBOR_BIN_DIR/uwsgi --ini $KARBOR_API_UWSGI_CONF" ""

    echo "Waiting for Karbor API to start..."
    if ! wait_for_service $SERVICE_TIMEOUT $KARBOR_API_ENDPOINT; then
        die $LINENO "karbor-api uwsgi did not start"
    fi
}

# stop_karbor_api_mod_wsgi() - Disable the api service and stop it.
function stop_karbor_api_mod_wsgi {
    disable_apache_site osapi_karbor
    restart_apache_server
}

function stop_karbor_api_uwsgi {
    remove_uwsgi_config "$KARBOR_API_UWSGI_CONF" "$KARBOR_API_UWSGI"
    stop_process karbor-api
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

function configure_providers {
    if is_swift_enabled; then
        echo_summary "Configuring Swift Bank"
        iniset $KARBOR_CONF_DIR/providers.d/openstack-infra.conf swift_client swift_key $SERVICE_PASSWORD
    fi
}

function create_karbor_cache_dir {

    # Delete existing dir
    sudo rm -rf $KARBOR_AUTH_CACHE_DIR
    sudo mkdir -p $KARBOR_AUTH_CACHE_DIR
    sudo chown `whoami` $KARBOR_AUTH_CACHE_DIR

}

function install_karborclient {
    if use_library_from_git "python-karborclient"; then
        echo_summary "Installing Karbor Client from git"
        git_clone $KARBORCLIENT_REPO $KARBORCLIENT_DIR $KARBORCLIENT_BRANCH
        setup_develop $KARBORCLIENT_DIR
    fi
}

is_karbor_enabled

if [[ "$Q_ENABLE_KARBOR" == "True" ]]; then
    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        echo summary "Karbor pre-install"
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        install_karborclient

        echo_summary "Installing Karbor"

        setup_package $KARBOR_DIR -e
        _create_karbor_conf_dir

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring Karbor"

        configure_karbor_api
        configure_providers

        if [[ "$KARBOR_DEPLOY" == "mod_wsgi" ]]; then
            karbor_config_apache_wsgi
        elif [[ "$KARBOR_DEPLOY" == "uwsgi" ]]; then
            karbor_config_uwsgi
        fi

        echo export PYTHONPATH=\$PYTHONPATH:$KARBOR_DIR >> $RC_DIR/.localrc.auto

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then

        echo_summary "Creating Karbor entities for auth service"
        create_karbor_accounts

        echo_summary "Initializing Karbor Service"

        if is_service_enabled $DATABASE_BACKENDS; then
            # (re)create karbor database
            recreate_database karbor utf8

            # Migrate karbor database
            $KARBOR_BIN_DIR/karbor-manage db sync
        fi
        if is_service_enabled karbor-api; then
            if [[ "$KARBOR_DEPLOY" == "mod_wsgi" ]]; then
                start_karbor_api_mod_wsgi
            elif [[ "$KARBOR_DEPLOY" == "uwsgi" ]]; then
                start_karbor_api_uwsgi
            fi
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
            if [[ "$KARBOR_DEPLOY" == "mod_wsgi" ]]; then
               stop_karbor_api_mod_wsgi
               clean_karbor_api_mod_wsgi
            elif [[ "$KARBOR_DEPLOY" == "uwsgi" ]]; then
               stop_karbor_api_uwsgi
               clean_karbor_api_uwsgi
           fi
        fi
        if is_service_enabled karbor-operationengine; then
           stop_process karbor-operationengine
        fi
        if is_service_enabled karbor-protection; then
           stop_process karbor-protection
        fi
    fi
fi
