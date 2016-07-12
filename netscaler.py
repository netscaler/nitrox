#!/usr/bin/env python

from functools import wraps
import logging
import socket
import re

from nssrc.com.citrix.netscaler.nitro.exception.nitro_exception \
    import nitro_exception
from nssrc.com.citrix.netscaler.nitro.resource.config.lb.lbvserver \
    import lbvserver
from nssrc.com.citrix.netscaler.nitro.service.nitro_service\
    import nitro_service
from nssrc.com.citrix.netscaler.nitro.resource.config.basic.servicegroup\
    import servicegroup
from nssrc.com.citrix.netscaler.nitro.resource.config.lb.lbvserver_servicegroup_binding\
    import lbvserver_servicegroup_binding
from nssrc.com.citrix.netscaler.nitro.resource.config.basic.servicegroup_servicegroupmember_binding\
    import servicegroup_servicegroupmember_binding


logger = logging.getLogger('docker_netscaler')


def ns_session_scope(func):
    @wraps(func)
    def login_logout(self, *args, **kwargs):
        self.ns_session = nitro_service(self.nsip, 'HTTP')
        self.ns_session.set_credential(self.nslogin, self.nspasswd)
        self.ns_session.timeout = 600
        self.ns_session.login()
        result = func(self, *args, **kwargs)
        self.ns_session.logout()
        self.ns_session = None
        return result
    return login_logout


class NetscalerInterface:

    def __init__(self, nsip, nslogin, nspasswd, app_info,
                 configure_frontends=False):
        self.nsip = nsip
        self.nslogin = nslogin
        self.nspasswd = nspasswd
        self.ns_session = None
        self.app_info = app_info
        """
        app_info expected structure:
        '{"appkey": "com.citrix.lb.appname",
          "apps": [{"name": "foo0", "lb_ip":"10.220.73.122", "lb_port":"443"},
                   {"name": "foo1", "lb_ip":"10.220.73.123", "lb_port":"80"},
                   {"name":"foo2"}, {"name":"foo3"}]}'
        """
        if configure_frontends:
            frontends = [(self._get_lb_name(l['name']), l['lb_ip'], l['lb_port'])
                         for l in self.app_info['apps']
                         if l.get('lb_ip') and l.get('lb_port')]
            for f in frontends:
                self.configure_lb_frontend(f[0], f[1], f[2])

    def _get_ns_compatible_name(self, app_name):
        return app_name.replace('/', '_').lstrip('_')
    
    def _get_lb_name(self, app_name):
        for app in self.app_info['apps']:
            if app['name'] == app_name:
                break
            
        if 'lb_name' in app:
            return app['lb_name']
        else:
            return self._get_ns_compatible_name(app_name)

    def _get_sg_name(self, app_name):
        for app in self.app_info['apps']:
            if app['name'] == app_name:
                break

        if 'sg_name' in app:
            return app['sg_name']
        else:
            return self._get_ns_compatible_name(app_name)

    def _create_service_group(self, grpname):
        try:
            svc_grp = servicegroup.get(self.ns_session, grpname)
            if (svc_grp.servicegroupname == grpname):
                logger.info("Service group %s already configured " % grpname)
                return
        except nitro_exception as e:
            pass
        svc_grp = servicegroup()
        svc_grp.servicegroupname = grpname
        svc_grp.servicetype = "HTTP"
        servicegroup.add(self.ns_session, svc_grp)

    def _create_lb(self, lbname, lbmethod, vip, port):
        try:
            lb = lbvserver.get(self.ns_session, lbname)
            if (lb.name == lbname) and \
                    (lb.ipv46 == vip) and \
                    (str(lb.port) == port):
                logger.info("LB %s is already configured " % lbname)
                return
            else:
                logger.info("LB %s is already configured with a different \
                            VIP/port : %s:%s\n" % (lb.name, lb.ipv46, lb.port))
                raise Exception("LB %s already configured with different VIP/\
                                port : %s:%s\n" % (lbname, lb.ipv46, lb.port))
        except nitro_exception as e:
            pass

        lb = lbvserver()
        lb.name = lbname
        lb.ipv46 = vip
        lb.servicetype = "HTTP"
        lb.port = port
        lb.lbmethod = lbmethod
        lbvserver.add(self.ns_session, lb)

    def _add_service(self, grpname, srvr_ip, srvr_port):
        try:
            bindings = servicegroup_servicegroupmember_binding.get(
                self.ns_session, grpname)
            for binding in bindings:
                if binding.ip == srvr_ip and str(binding.port) == srvr_port:
                    logger.info("Service %s:%s is already bound to service \
                                group %s " % (srvr_ip, srvr_port, grpname))
                    return

        except nitro_exception as e:
            pass
        binding = servicegroup_servicegroupmember_binding()
        binding.servicegroupname = grpname
        binding.ip = srvr_ip
        binding.port = srvr_port
        servicegroup_servicegroupmember_binding.add(self.ns_session, binding)

    def _bind_service_group_lb(self, lbname, grpname):
        try:
            bindings = lbvserver_servicegroup_binding.get(self.ns_session,
                                                          lbname)
            for b in bindings:
                if b.name == lbname and b.servicegroupname == grpname:
                    logger.info("LB %s is already bound to service group %s"
                                % (lbname, grpname))
                    return
        except nitro_exception as e:
            pass

        binding = lbvserver_servicegroup_binding()
        binding.name = lbname
        binding.servicegroupname = grpname
        lbvserver_servicegroup_binding.add(self.ns_session, binding)

    def _configure_services(self, grpname, srvrs):
        srvrs_new= []
        for s in srvrs:
            if not re.match('^[0-9\.]+$', s[0]):
                srvrs_new.append((socket.gethostbyname(s[0]), s[1]))
        srvrs = srvrs_new
        
        to_add = srvrs
        to_remove = []
        try:
            bindings = servicegroup_servicegroupmember_binding.get(
                self.ns_session, grpname)
            existing = [(b.ip, b.port) for b in bindings if b.port != 0]
            to_remove = list(set(existing) - set(srvrs))
            to_add = list(set(srvrs) - set(existing))
            to_leave = list(set(srvrs) & set(existing))
        except nitro_exception as e:
            pass  # no bindings
        for s in to_remove:
            binding = servicegroup_servicegroupmember_binding()
            binding.servicegroupname = grpname
            binding.ip = s[0]
            binding.port = s[1]
            logger.info("Unbinding %s:%s from service group %s " % (s[0], s[1],
                        grpname))
            servicegroup_servicegroupmember_binding.delete(self.ns_session,
                                                           binding)
        for s in to_add:
            binding = servicegroup_servicegroupmember_binding()
            binding.servicegroupname = grpname
            binding.ip = s[0]
            binding.port = s[1]
            logger.info("Binding %s:%s from service group %s " %
                        (s[0], s[1], grpname))
            servicegroup_servicegroupmember_binding.add(self.ns_session,
                                                        binding)
        for s in to_leave:
            logger.info("%s:%s is already bound to  service group %s"
                        % (s[0], s[1], grpname))

    @ns_session_scope
    def configure_lb_frontend(self, lbname, lb_vip, lb_port):
        try:
            self._create_lb(lbname, "ROUNDROBIN", lb_vip, lb_port)
        except nitro_exception as ne:
            logger.warn("Nitro Exception: %s" % ne.message)
        except Exception as e:
            logger.warn("Exception: %s" % e.message)

    @ns_session_scope
    def configure_lb(self, lbname, lb_vip, lb_ports, srvrs):
        try:
            self._create_lb(lbname, "ROUNDROBIN", lb_vip, lb_ports)
            self._create_service_group(lbname)  # Reuse lbname
            self._bind_service_group_lb(lbname, lbname)
            self._configure_services(lbname, srvrs)
        except nitro_exception as ne:
            logger.warn("Nitro Exception: %s" % ne.message)
        except Exception as e:
            logger.warn("Exception: %s" % e.message)

    @ns_session_scope
    def configure_app(self, app,  srvrs):
        try:
            lbname = self._get_lb_name(app)
            sgname = self._get_sg_name(app)
            self._create_service_group(sgname)
            self._bind_service_group_lb(lbname, sgname)
            self._configure_services(sgname, srvrs)
        except nitro_exception as ne:
            logger.warn("Nitro Exception: %s" % ne.message)
        except Exception as e:
            logger.warn("Exception: %s" % e.message)
