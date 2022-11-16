from unittest import TestCase
from agplibs.clients.fac import FonivaApiClient
from agplibs.clients.sac import SugarApiClient
from agplibs.utils.sugar import Contact
from agplibs.utils.foniva import Campaign
from agplibs.logics.tag import Tagger, Tag
from src.service import VendeurParticulier
import datetime
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

import math


class VendeurParticulierTest(TestCase):    
    
    def setUp(self):
        
        self.vp = VendeurParticulier()
        self.sac_client = SugarApiClient()
        self.fac_client = FonivaApiClient()
        self.tdd_dbid = 61
        self.vp_dbid = 22
        self.ratio = 0.5
    
    def test_get_end_dates(self):
        
        end_dates = self.vp.get_end_dates()
        self.assertLess(end_dates[0], (datetime.now() + relativedelta(years=1)))
        self.assertGreater(end_dates[-1], datetime(2001, 8, 1))
        
    
    def test_get_start_dates(self):
        
        start_date = self.vp.get_start_dates() 
        self.assertLess(start_date[0], (datetime.now() + relativedelta(years=1)))
        self.assertGreater(start_date[-1], datetime(2001, 8, 1))
    
    
    def test_filter(self):
        
        date_in_range = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        date_not_in_range = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        
        test_contact_auto_in_range = [{'id': '2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46', 'date_modified': '2021-07-25T10:12:59-04:00', 
                         'first_name': 'Tony', 'last_name': 'Stark', 'phone_home': '5819931665', 'date_renouvellement_auto_c': date_in_range, 
                         'date_renouvellement_maison_c': '', 'statut_appel_c': 'Pas Interesse', 'source_principale_c': '', 
                         'source_secondaire_c': 'Agent Particulier', '_acl': {'fields': {}}, '_module': 'Contacts'}]
        
        filtered_list = self.vp.dates_filter(test_contact_auto_in_range)
        self.assertEqual(len(filtered_list), 1)
        self.assertIn('2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46', filtered_list[0][0])
        
        test_contact_auto_not_in_range = [{'id': '2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46', 'date_modified': '2021-07-25T10:12:59-04:00', 
                         'first_name': 'Tony', 'last_name': 'Stark', 'phone_home': '5819931665', 'date_renouvellement_auto_c': date_not_in_range, 
                         'date_renouvellement_maison_c': '', 'statut_appel_c': 'Pas Interesse', 'source_principale_c': '', 
                         'source_secondaire_c': 'Agent Particulier', '_acl': {'fields': {}}, '_module': 'Contacts'}]
        
        filtered_list = self.vp.dates_filter(test_contact_auto_not_in_range)
        self.assertEqual(len(filtered_list), 0)
        
        
        test_contact_habit_in_range = [{'id': '2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46', 'date_modified': '2021-07-25T10:12:59-04:00', 
                         'first_name': 'Tony', 'last_name': 'Stark', 'phone_home': '5819931665', 'date_renouvellement_auto_c': '', 
                         'date_renouvellement_maison_c': date_in_range, 'statut_appel_c': 'Pas Interesse', 'source_principale_c': '', 
                         'source_secondaire_c': 'Agent Particulier', '_acl': {'fields': {}}, '_module': 'Contacts'}]
        
        filtered_list = self.vp.dates_filter(test_contact_habit_in_range)
        self.assertEqual(len(filtered_list), 1)
        self.assertIn('2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46', filtered_list[0][0])
        
        
        test_contact_habit_not_in_range = [{'id': '2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46', 'date_modified': '2021-07-25T10:12:59-04:00', 
                         'first_name': 'Tony', 'last_name': 'Stark', 'phone_home': '5819931665', 'date_renouvellement_auto_c': '', 
                         'date_renouvellement_maison_c': date_not_in_range, 'statut_appel_c': 'Pas Interesse', 'source_principale_c': '', 
                         'source_secondaire_c': 'Agent Particulier', '_acl': {'fields': {}}, '_module': 'Contacts'}]
        
        filtered_list = self.vp.dates_filter(test_contact_habit_not_in_range)
        self.assertEqual(len(filtered_list), 0)
        
        
    def test_remove_double_by_phone(self):
        
        test_phone_dates_autres = [
            ['','','','4189304928'],
            ['','','','3452189724'],
            ['','','','0825374821']
        ]
        
        test_phone_dates_intact = [
            ['','','','4189304928'],
            ['','','','0000000000'],
            ['','','','4352617284']
        ]
        
        test_phone_dates_autres, test_phone_dates_intact = self.vp.remove_double_by_phone(test_phone_dates_autres, test_phone_dates_intact)
        
        self.assertEqual(len(test_phone_dates_autres), 3)
        self.assertEqual(len(test_phone_dates_intact), 2)
        
    
    def test_remove_in_list_if_in_foniva(self):
        
        foniva_list = self.fac_client.get_all(self.tdd_dbid)
                    
        for i in foniva_list:
            
            self.fac_client.delete(i['number'], self.tdd_dbid)
        
        self.fac_client.post(querystring={"number": "4189304928", "dbid": self.tdd_dbid, "custom": "2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46"})
        
        list_with_double_in_foniva = [['2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46'],
                                      ['23ad0bc2-5c61-11e8-b05d-0699afa2cd79']
                                      ]
                
        clear_list = self.vp.remove_sugarid_from_foniva(list_with_double_in_foniva, self.tdd_dbid)
        self.assertEqual(len(list_with_double_in_foniva), 1)
        self.fac_client.delete('4189304928', self.tdd_dbid)
        foniva_list = self.fac_client.get_all(self.tdd_dbid)
        self.assertEqual(len(foniva_list), 0)
    

    def test_merge(self):
                
        test_dates_autres = ['1','1','1','1',  '1','1','1','1',  '1','1','1','1',  '1','1','1','1',  '1','1','1','1']
        test_dates_intact = ['2','2','2','2','2','2']
        validation_list = ['1', '1', '1', '1', '1', '1', '1', '2', '1', '1', '1', '1', '1', '1', '2', '1', '1', '1', '1', '1', '1', '2', '1']
        
        mixed_list = self.vp.mix_lists(test_dates_intact, test_dates_autres, self.ratio)

        self.assertEqual(mixed_list, validation_list)
        
        
        
  
    def test_update(self):
        
        contact_test = [
            ['wefwfrewrfer','j','t','4189304928','','','',''],
            ['fsdkkljknlxx','d','p','3452189724','','','',''],
            ['ioiiepsisdcl','y','m','0825374821','','','','']
        ]
        
        self.vp.update(contact_test, self.tdd_dbid)
        foniva_list = self.fac_client.get_all(self.tdd_dbid)
        self.assertEqual(len(foniva_list), 3)
        
        contact_test_updated = contact_test = [
            ['wefwfrewrfer','j','t','4189304928','','','',''],
            ['fsdkkljknlxx','d','p','3452189724','','','',''],
            ['ioiiepsisdcl','y','m','0825374821','','','',''],
            ['kugkuhqwdiha','t','c','5819932345','','','','']
        ]
        
        self.vp.update(contact_test_updated, self.tdd_dbid)
        foniva_list = self.fac_client.get_all(self.tdd_dbid)
        self.assertEqual(len(foniva_list), 4)
        
        contact_test_remove = contact_test = [
            ['kugkuhqwdiha','t','c','5819932345','','','','']
        ]
        
        self.vp.update(contact_test_remove, self.tdd_dbid)
        foniva_list = self.fac_client.get_all(self.tdd_dbid)
        self.assertEqual(len(foniva_list), 1)
        
        self.fac_client.delete('5819932345', self.tdd_dbid)
        
        
    def test_need_to_update_phone(self):
        
        self.fac_client.post(querystring={"number": "4189304928", "dbid": self.tdd_dbid, "custom": "2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46"})
        
        foniva_list = self.fac_client.get_all(self.tdd_dbid)
        
        dates_finales_test = [[ "2ee0e91e-cc1c-11ea-b04d-06f2b4fb7f46", 'Tony', 'Stark','1112223333','date_renouvellement_auto_c',
                               'statut_appel_c', 'source_principale_c','source_secondaire_c']]
        
        for i in dates_finales_test:
        
            self.vp.need_to_update_phone(foniva_list, i[3], i[0], self.tdd_dbid)
            
        foniva_list = self.fac_client.get_all(self.tdd_dbid)
        
        for i in foniva_list:
            
            number = i['number']
            self.assertEqual(number, "1112223333")
            
        self.fac_client.delete("1112223333", self.tdd_dbid)
        # self.fac_client.delete("4189304928", self.tdd_dbid)
        
        

        

        
        
        


























