from unittest import TestCase
from src.service import TagVendeurParticulier
from agplibs.utils.genesys import Outbound
from agplibs.genesys.enums import GenesysCampaign
import dotenv
import logging 
import os

dotenv.load_dotenv()
logging.basicConfig(level = logging.INFO)


class VPTagTest(TestCase):    
    
    def setUp(self):
        self.__vp_tag = TagVendeurParticulier(None)
        self.outbound = Outbound(os.getenv('CLIENT_ID'), os.getenv('CLIENT_SECRET'))
        self.__clic_list_id =  self.outbound.get_contact_list_id_from_a_campaign_name(GenesysCampaign.C_CLIC_ASSURE)
        

    def test_tag_get_contacts_clicassure(self):
        
        clic_genesys_list_number = list(map(lambda f: f["number"], self.outbound.get_all_contacts_from_a_contact_list(self.__clic_list_id)))
        self.assertIn("4383381311", clic_genesys_list_number)

        contacts_clic_assure = self.__vp_tag.get_contacts_clicassure_tag()
        clic_genesys_list_phone_home = list(map(lambda f: f["phone_home"], contacts_clic_assure))
        self.assertIn("4383381311", clic_genesys_list_phone_home)
        
        
    def test_tag_contacts_clicassure(self):    
        
        clic_genesys_list_number = list(map(lambda f: f["number"], self.outbound.get_all_contacts_from_a_contact_list(self.__clic_list_id)))
        
        contact_clicassure_tag = self.__vp_tag.get_contacts_clicassure_tag()

        contacts_clics = list(filter(lambda c: self.__vp_tag.validation_clicassure(c, clic_genesys_list_number),
                                               contact_clicassure_tag))

        self.assertNotIn("4383381311", list(map(lambda f: f["phone_home"], contacts_clics)))




    