#!/usr/bin/env python3
from pyzabbix.api import ZabbixAPI
import json
import os
import difflib
import sys
from xml.dom import minidom
import xml.etree.ElementTree as ET
from multiprocessing.dummy import Pool as ThreadPool
from functools import partial
import logging
import yaml
import argparse

WORK_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG_PATH = WORK_DIR + '/config.yml'

# Init logging level
logging.basicConfig(level=logging.INFO)


class ZapiHelper(object):
    def __init__(self, zbx_api_config):
        self.zapi_url = zbx_api_config.get('zapi_url', 'zapi_url')
        self.zapi_user = zbx_api_config.get('user', 'user')
        self.zapi_password = zbx_api_config.get('password', 'password')
        self.supported_api_major_versions = [
            '3.4'
        ]
        self.output_formats = [
            'refer',
            'shorten',
            'extend'
        ]
        self.import_export_formats = [
            'xml',
            'json'
        ]
        self.__init_api()

    def __validate_api_versions(self, api_v):
        """check supported api versions"""
        if api_v[0:3] not in self.supported_api_major_versions:
            msg = 'Unsupported api version {0}.' \
                  'Supported versions are: {1}' \
                  .format(api_v[0:3], self.supported_api_major_versions)
            raise RuntimeError(msg)

    def __validate_output_format(self, out_format):
        """check supported output format"""
        if out_format not in self.output_formats:
            msg = 'Unsupported output format {0}.' \
                  'Supported formats are: {1}' \
                  .format(out_format, self.output_formas)
            raise RuntimeError(msg)

    def __valide_export_format(self, export_format):
        """check supported export format"""
        if export_format not in self.import_export_formats:
            msg = 'Unsupported export format {0}.' \
                  'Supported formats are: {1}' \
                  .format(export_format, self.import_export_formats)
            raise RuntimeError(msg)

    def __valide_import_format(self, import_format):
        """check supported import format"""
        if import_format not in self.import_export_formats:
            msg = 'Unsupported import format {0}.' \
                  'Supported formats are: {1}' \
                  .format(import_format, self.import_export_formats)
            raise RuntimeError(msg)

    def __init_api(self):
        self.zapi = ZabbixAPI(
            self.zapi_url, user=self.zapi_user, password=self.zapi_password)
        self.zapi_version = self.__validate_api_versions(
            self.zapi.do_request('apiinfo.version')['result'])

    def get_hosts(self, hosts=[], output='extend'):
        """ get hosts from zabbix api
            if hosts=[] return all hosts
        """
        self.__validate_output_format(output)
        hosts = self.zapi.host.get(
            filter={'host': hosts}, output=output)
        return hosts

    def get_templates(self, templates=[], output='extend'):
        """ get templates from zabbix api
            if templates=[] return all templates
        """
        self.__validate_output_format(output)
        templates = self.zapi.template.get(
            filter={'host': templates}, output=output)
        res = {i['name']: i['templateid'] for i in templates}
        return res

    def api_export(self, export_obj, obj_id, export_format):
        """ export objects from api
        """
        self.__valide_export_format(export_format)
        res = self.zapi.configuration.export(
            options={export_obj: [obj_id]}, format=export_format)
        return res

    def api_import(self, import_format, import_rules, import_source):
        """ import objects to zabbix
        """
        self.__valide_import_format(import_format)
        args = {
            'rules': import_rules,
            'format': import_format,
            'source': import_source
        }
        res = self.zapi.do_request('configuration.import', args)
        return res


class ZabbixTemplate(ZapiHelper):
    """ base template class """
    @staticmethod
    def write_to_file(data, file_name):
        with open(file_name, 'w') as f:
            f.write(data)

    @staticmethod
    def load_file(fname):
        with open(fname) as f:
            raw = f.read()
        return raw

    def export_template(self, name):
        """retun template from api"""
        msg = "Method should return template"
        raise NotImplementedError(msg)

    def load_template_from_file(self, fname):
        """load template from api to file"""
        msg = "Method should load template from file"
        raise NotImplementedError(msg)

    def save_template_to_file(self, name, fname):
        """save template from api to file"""
        msg = "Method should save template to file"
        raise NotImplementedError(msg)

    def compare(self):
        """compare templates from api and from file"""
        msg = "Method should compare template " \
              "form file and from server"
        raise NotImplementedError(msg)

    def import_template(self, fname):
        """import template from file
        """
        msg = "subclass {} should import template from file" \
              .format(self.__class__.__name__)
        raise NotImplementedError(msg)


class ZabbixTemplateXML(ZabbixTemplate):
    def __init__(self, zbx_api_config):
        super().__init__(zbx_api_config)

    def filter_xml(self, data):
        """Remove space string, empty strings and <?xml version="1.0" ?>
           from xml
        """
        return os.linesep.join(
                [
                    s for s in self.xml_pretty(data).splitlines()
                    if (not s.isspace()
                        and '<?xml version="1.0" ?>' not in s
                        and s != '')
                ])

    @staticmethod
    def xml_pretty(xml_tree, change_indent=True, indent="    "):
        """Return a pretty-printed XML string.
        """
        rough_string = ET.tostring(xml_tree, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        if change_indent:
            return reparsed.toprettyxml(indent=indent)
        return reparsed.toprettyxml()

    @staticmethod
    def get_template_name_xml(xml_tree):
        find_templates = xml_tree.find('templates')
        return find_templates.find('template').find('template').text

    @staticmethod
    def xml_tree(raw):
        return ET.fromstring(raw)

    @staticmethod
    def remove_date(xml_tree):
        date = xml_tree.find('date')
        if date is not None:
            xml_tree.remove(date)
        return xml_tree

    def prepare_export_xml(self, raw):
        xml_tree = self.xml_tree(raw)
        xml_tree = self.remove_date(xml_tree)
        return xml_tree

    def prepare_import_xml(self, raw):
        xml_tree = self.xml_tree(raw)
        xml_tree = self.remove_date(xml_tree)
        name = self.get_template_name_xml(xml_tree)
        return [name, xml_tree]

    def export_template_by_name(self, name):
        try:
            templateid = self.get_templates(templates=[name])[name]
            return self.export_template(templateid)
        except KeyError:
            logging.debug('Template "{}" not found'.format(name))
            return {}

    def export_template(self, templateid):
        raw = self.api_export('templates', templateid, 'xml')
        xml_tree = self.prepare_export_xml(raw)
        data = self.filter_xml(xml_tree)
        return data

    def save_template_to_file(self, dest_dir, name, templateid=None):
        try:
            if not templateid:
                data = self.export_template_by_name(name)
            else:
                data = self.export_template(templateid)
            if not data:
                msg = 'Template "{}" not found'.format(name)
                exit(0)
            fname = dest_dir + '/' + name.replace(' ', '_') + '.xml'
            self.write_to_file(data, fname)
            msg = 'Save "{0}" to {1}'.format(name, fname)
        except Exception as e:
            logging.debug(e, exc_info=True)
            msg = 'an error "{0}" occurred '\
                  'while saving "{1}"'\
                  .format(e, name, fname)
        finally:
            return msg

    def load_xml(self, file_name):
        try:
            raw = self.load_file(file_name)
            name, xml_tree = self.prepare_import_xml(raw)
            data = self.filter_xml(xml_tree)
            return [name, data]
        except IOError as e:
            raise RuntimeError("Config file not found: {}".format(e))

    def compare(self, fname):
        try:
            name, xml_from_file = self.load_xml(fname)
            xml_from_server = self.export_template_by_name(name)
            if xml_from_server:
                diff = list(
                    difflib.unified_diff(
                        xml_from_server.split('\n'),
                        xml_from_file.split('\n'),
                        name,
                        fname,
                        lineterm=''
                    )
                )
                if diff:
                    return diff
                else:
                    return '"{0}" and {1} have no differences {2}' \
                           .format(name, fname, diff)
            else:
                return 'Template "{}" not found'.format(name)
        except Exception as e:
            logging.debug(e, exc_info=True)
            msg = 'an error "{0}" occurred '\
                  'while compare {1}'\
                  .format(e, fname)
            return msg

    def import_template(self, import_rules, fname):
        try:
            name, import_source = self.load_xml(fname)
            res = self.api_import('xml', import_rules, import_source)
            return 'Import ' + name + ' ' + str(res)
        except Exception as e:
            logging.debug(e, exc_info=True)
            msg = 'an error "{0}" occurred '\
                  'while import {1}'\
                  .format(e, fname)
            return msg


# functions
def get_params(parser):
    parser.add_argument(
        "-a", "--export_all",
        dest="export_all",
        default=False,
        action='store_true',
        help="export all templates")

    parser.add_argument(
        "-e", "--export",
        dest="export_templates",
        nargs="+",
        help="export template",
        metavar="'Template OS Linux' 'Template OS Windows'")

    parser.add_argument(
        "-c", "--compare",
        dest="compare",
        nargs="+",
        help="compare template",
        metavar="'Template OS Linux' 'Template OS Windows'")

    parser.add_argument(
        "-i", "--import",
        dest="import_templates",
        nargs="+",
        help="import templates",
        metavar="test.xml test")

    parser.add_argument(
        "-d", "--dest_dir",
        dest="dest_dir",
        metavar='export',
        help="export destination dir. Default {}/exports".format(WORK_DIR))

    args = parser.parse_args()
    return args


def get_cls_by_format(api_format, config):
    supported_formats = {
        'xml': ZabbixTemplateXML(config.get('api'))
    }
    try:
        return supported_formats[api_format]
    except KeyError:
        msg = "Unsupported API format: {}." \
              "Supported format are: {}" \
              .format(api_format, supported_formats.keys())
        raise RuntimeError(msg)


def multiproc_worker(pool_limit, map_funk, work_list):
    pool = ThreadPool(pool_limit)
    len_work = len(work_list)
    if len_work < pool_limit:
        pool = ThreadPool(len_work)
    res = pool.map(map_funk, work_list)
    pool.close()
    pool.join()
    return res


def validate_args(params, parser):
    """ validate args counts
    """
    data = [
        params.export_all,
        params.import_templates,
        params.compare,
        params.export_templates
    ]
    res = [i for i in data if i]
    if len(res) > 1:
        msg = 'Too many args ' \
              'Please use only export_all or '\
              'only import_templates or ' \
              'only compare or ' \
              'only export_templates'
        raise RuntimeError(msg)
    if len(res) < 1:
        parser.print_help()
        sys.exit(1)


def load_config(config_file):
    try:
        with open(config_file, 'r') as stream:
            config = yaml.load(stream)
        return config
    except IOError as e:
        raise RuntimeError("Config file not found: {}".format(e))


def main():
    try:
        # configs and instance
        config = load_config(WORK_DIR + '/config.yml')
        dest_dir = WORK_DIR + '/exports'
        import_rules = config.get('import_rules')
        api_format = config.get('api_format')
        z = get_cls_by_format(api_format, config)
        parser = argparse.ArgumentParser()
        # get args
        params = get_params(parser)
        validate_args(params, parser)
        export_all = params.export_all
        compare = params.compare
        import_templates = params.import_templates
        export_templates = params.export_templates
        if params.dest_dir:
            dest_dir = params.dest_dir
        # main logic
        prepare_map_func = partial(z.save_template_to_file, dest_dir)
        if export_all:
            map_func = lambda args: prepare_map_func(*args)
            work_list = z.get_templates().items()
        elif export_templates:
            work_list = export_templates
            map_func = prepare_map_func
        elif compare:
            map_func = z.compare
            work_list = compare
        elif import_templates:
            work_list = import_templates
            map_func = partial(z.import_template, import_rules)
        res = multiproc_worker(config.get('pool_limit'), map_func, work_list)
        print(json.dumps(res, indent=4, sort_keys=True))
    except Exception as e:
        logging.error(e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
