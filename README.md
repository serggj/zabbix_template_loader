Intro
=====
- Скрипт для экспорта и импорта конфигурации(templates) zabbix через api
- подерживаемый формат xml
- параметры задаваемые в конфиге 
  - параметры подключения 
  - параметры импорта
  - количество тредов
- одновременно можно задать только один из ключей -i, -c, -e  или -a  

Подготовка к работе 
===================
1. установить зависимости из requirements.txt     
2. создать конфиг(config.yml) в рабочей директории 
    (по умолчанию директория со скриптом), пример есть в config.yml.sample

Help
====

```
optional arguments:
  -h, 
  --help                                                показать справку и выйти

  -a, 
  --export_all                                          экспортировать все шаблоны в директорию, директорию можно задать через ключ -d 

  -e, 
  --export 'Template OS Linux' 'Template OS Windows'    экспотировать шаблоны по имени (имена разделяются пробелами)
  -c,  
  --compare Template_Guest.xml Template_text.xml        сравнить конфигурацию в файлах с конфигурацией в базе zabbix

  -i, 
  --import  Template_Guest.xml Template_text.xmi        импортировать шаблоны из файлов в базу zabbix

  -d, 
  --dest_dir ./export                                   Задать директортю для экспорта. По умолчанию = "WORK_DIR + /exports"
```


Примеры
========
1. Сравнение 2 шаблонов из файлов с шаблонами в базе
```
./zabbix_template_loader.py  -c exports/Template_VM_VMware_Guest.xml exports/Template_Net_Juniper_SNMPv2.xml 
```
2. Импорт 2 шаблонов 
```
./zabbix_template_loader.py  -i exports/Template_VM_VMware_Guest.xml exports/Template_Net_Juniper_SNMPv2.xml 
```
3. Экспорт 2 шаблонов 
```
./zabbix_template_loader.py  -e 'Template OS Linux' 'Template OS Windows'

```

requirements
============
python >= 3.5   
py-zabbix==1.1.3    
PyYAML==3.12    
