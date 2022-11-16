from re import T
from agplibs.clients.sac import SugarApiClient
from agplibs.clients.dorm import DormApiClient
from agplibs.utils.utils import chunks
# from agplibs.utils.genesys import Campaign, Outbound
from agplibs.logics.tag import Tagger, Tag
from agplibs.utils.loader import Loader
from agplibs.utils.slack import log_on_slack
from agplibs.services.service import ServiceSuper, ServiceStatus
from agplibs.logics.container import LinksToContact, LinkRessource, ContactModel
from agplibs.utils.genesys import Outbound
from agplibs.genesys.enums import GenesysCampaign
from enums import LangueCommunication
import time
import datetime
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from pprint import pprint
import schedule
import traceback
import os 
import logging 
import dotenv

dotenv.load_dotenv()
logging.basicConfig(level = logging.INFO)

## ! change get_all_contacts_from_a_contact_list time sleep to 60 sec
class RealTimeCampaign:
            
    class VendeurParticulier:   
        max_attempts = 5
        range_days = 35
        ratio = 1
   
   
class TagVendeurParticulier:
    
    def __init__(self, file_logger):
        
        self.sac_client = SugarApiClient()
        self.dorm_client = DormApiClient()
        self.file_logger = file_logger

    def __init_api_client(self):
        self.outbound = Outbound(os.getenv('CLIENT_ID'), os.getenv('CLIENT_SECRET'))
      
      
    def get_contacts_tag(self):
        
        return self.sac_client.get('Contacts', 
                            filters={"filter": [
                                {"statut_client_c": "Prospect"},
                                {"preferred_language_c": LangueCommunication.FRANCAIS},
                                {"source_secondaire_c":
                                    {"$not_in": [
                                        "Collecte Web", 
                                        "SNV", 
                                        "Soumission Web", 
                                        "Vendeur Particulier",
                                        "ClicAssure",
                                        "Vendeur Particulier Anglais",
                                        "Agent Particulier Anglais",
                                        "Autres Statuts Anglais",
                                        "Numero Hors Service"
                                    ]} 
                                },
                                {"$or":[   
                                    {"statut_appel_c": "Date Collectee"},
                                    {"statut_appel_c": "Intact Dates Collectees"},
                                    {"statut_appel_c": "Date Collectee Relance"}
                                ]}, 
                            ]},
                            fields=['id'], max_num=5000)
    
   
    def get_contacts_clicassure_tag(self):
    
        return self.sac_client.get('Contacts', 
                            filters={"filter": [
                                {"statut_client_c": "Prospect"},
                                {"preferred_language_c": LangueCommunication.FRANCAIS},
                                {"source_secondaire_c": "ClicAssure"}, 
                                
                                {"$or":[   
                                    {"statut_appel_c": "Date Collectee"},
                                    {"statut_appel_c": "Intact Dates Collectees"},
                                    {"statut_appel_c": "Date Collectee Relance"}
                                ]}, 
                            ]},
                            fields=['id', 'validation_c', 'phone_home'], max_num=5000)

    
    def get_contacts_soumission_web_tag(self):
    
        return self.sac_client.get('Contacts', 
                            filters={"filter": [
                                {"statut_client_c": "Prospect"},
                                {"preferred_language_c": LangueCommunication.FRANCAIS},
                                {"source_secondaire_c": "Soumission Web"}, 
                                {"$or":[   
                                    {"statut_appel_c": "Date Collectee"},
                                    {"statut_appel_c": "Intact Dates Collectees"},
                                    {"statut_appel_c": "Date Collectee Relance"}
                                ]}, 
                            ]},
                            fields=['id', 'validation_c', 'phone_home'], max_num=5000)
       
        
    def validation_clicassure(self, contact, genesys_list):

        return  contact['validation_c'] == 'clicassure' or \
               (contact['validation_c'] == '' and \
                not any(contact['phone_home'] in f for f in genesys_list))
    
    
    def validation_soumission_web(self, contact, genesys_list):

        return  contact['validation_c'] == 'soumission_web_fait' or \
               (contact['validation_c'] == '' and \
                not any(contact['phone_home'] in f for f in genesys_list))
     
        
    def job(self):
        
        self.file_logger.info(f"Tag de la source secondaire START")
        self.__init_api_client()

        clic_genesys_list_id = self.outbound.get_contact_list_id_from_a_campaign_name(GenesysCampaign.C_CLIC_ASSURE)
        soum_web_genesys_list_id = self.outbound.get_contact_list_id_from_a_campaign_name(GenesysCampaign.C_SOUMISSION_WEB)
               
        clic_genesys_list = list(map(lambda f: f["number"], self.outbound.get_all_contacts_from_a_contact_list(clic_genesys_list_id)))
        soum_web_genesys_list = list(map(lambda f: f["number"], self.outbound.get_all_contacts_from_a_contact_list(soum_web_genesys_list_id)))
        
        contacts = self.get_contacts_tag()
        contacts_clics = list(filter(lambda c: self.validation_clicassure(c, clic_genesys_list),
                                               self.get_contacts_clicassure_tag()))

        contacts_soumissions_web  = list(filter(lambda c: self.validation_soumission_web(c, soum_web_genesys_list),
                                                          self.get_contacts_soumission_web_tag()))
                                                        
        contacts_ids = list(map( lambda c: c['id'], contacts ))
        contacts_clics_ids = list(map( lambda c: c['id'], contacts_clics ))
        contacts_soum_web_ids = list(map( lambda c: c['id'], contacts_soumissions_web ))
        
        # ! DEBUG
        #Tag des contacts
        Tagger.bulk_create(self.sac_client, 
                           self.dorm_client, 
                           contacts_ids + contacts_clics_ids + contacts_soum_web_ids, 
                           source_secondaire=Tag.SourceSecondaire.VENDEUR_PARTICULIER 
                        )

        # #Update du champ validation_c pour les contacts clics 
        self.sac_client.mass_update("Contacts", 
                                    contacts_clics_ids + contacts_soum_web_ids, 
                                    "validation_c", "")

        self.file_logger.info(f"Contacts Vendeur : {len(contacts_ids)}")
        self.file_logger.info(f"Contacts Clics Assure : {len(contacts_clics_ids)}")
        self.file_logger.info(f"Contacts Soumission Web : {len(contacts_soum_web_ids)}")

        self.file_logger.info(f"Tag de la source secondaire END")


class VendeurParticulier:
    
    def __init__(self, file_logger=None):
        
        self.sac_client = SugarApiClient()
        self.dorm_client = DormApiClient()
        self.current_time = datetime.now()
        self.max_attempts = RealTimeCampaign.VendeurParticulier.max_attempts
        self.range_days = RealTimeCampaign.VendeurParticulier.range_days
        self.ratio = RealTimeCampaign.VendeurParticulier.ratio
        self.file_logger = file_logger

    def __init_api_client(self):
        self.outbound = Outbound(os.getenv('CLIENT_ID'), os.getenv('CLIENT_SECRET'))
        
    def get_end_dates(self):
        
        tmp = self.current_time + timedelta(days= self.range_days)
        fortyfive_past_days_years = []        
        
        while tmp > datetime(2001, 8, 1):
            
            fortyfive_past_days_years.append(tmp)
            tmp = tmp - relativedelta(years=1)
                    
        return fortyfive_past_days_years


    def past_days_rdv(self):
        
        return (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')


    def get_start_dates(self):

        tmp = self.current_time
        current_time_years=[]

        while tmp > datetime(2001, 8, 1):

            current_time_years.append(tmp)
            tmp = tmp - relativedelta(years=1)
            
        return current_time_years
         
         
    def get_dates_autres(self, limit=None):
        
        print('GET Dates Autres')
        
        return self.sac_client.get('Contacts', 
                            filters={"filter": [
                                {"statut_client_c": "Prospect"},
                                {"preferred_language_c": LangueCommunication.FRANCAIS},
                                {"source_secondaire_c": "Vendeur Particulier"},
                                {"statut_appel_c":
                                    {"$in": ["Date Collectee", "Date Collectee Relance"]}
                                },
                                {"$or":[
                                    {"rdv_contact_c": {"$empty":""}},                                    
                                    {"rdv_contact_c": {"$lt": f"{self.past_days_rdv()}"}}
                                ]}, 
                            ]},
                            limit=limit,
                            fields=['id', 'first_name', 'last_name', 'phone_home', 'date_renouvellement_auto_c','date_renouvellement_maison_c', 
                                    'statut_appel_c', 'source_principale_c', 'source_secondaire_c', 'salutation', 'date_renouv_vehicule_loisir_c'], 
                            max_num=5000)


    def get_dates_intact(self, limit=None):
        
        print('GET Dates Intact')
        
        return self.sac_client.get('Contacts', 
                            filters={"filter": [
                                {"statut_client_c": "Prospect"},
                                {"preferred_language_c": LangueCommunication.FRANCAIS},
                                {"statut_appel_c": "Intact Dates Collectees"},
                                {"source_secondaire_c": "Vendeur Particulier"},                                
                                {"$or":[
                                    {"rdv_contact_c": {"$empty":""}},                                    
                                    {"rdv_contact_c": {"$lt": f"{self.past_days_rdv()}"}}
                                ]},                                
                            ]},
                            fields=['id', 'first_name', 'last_name', 'phone_home', 'date_renouvellement_auto_c', 
                                    'date_renouvellement_maison_c', 'statut_appel_c', 'source_principale_c', 'source_secondaire_c', 'salutation', 'date_renouv_vehicule_loisir_c'], 
                            limit=limit,
                            max_num=5000)
        

    def is_in_range(self, date, ranges):
        
        is_in_range = False
        
        for x, y in ranges:
            
            if datetime.strptime(date, '%Y-%m-%d') >= x and datetime.strptime(date, '%Y-%m-%d') <= y :
                
                is_in_range = True
                break
            
        return is_in_range


    def dates_are_in_ranges(self, contact_model, ranges):

        """Retourne vrai si une des dates de renouvellement du contacts est 
           comprise inclusivent entre un range de date"""
        
        s_contact = contact_model.contact
        date_renouvellement_auto = s_contact['date_renouvellement_auto_c']
        date_renouvellement_habit = s_contact['date_renouvellement_maison_c']
        date_renouvellement_loisir = s_contact['date_renouv_vehicule_loisir_c'] 
        
        
        if date_renouvellement_auto != '':
           return self.is_in_range(date_renouvellement_auto, ranges)

        elif date_renouvellement_habit != '':
            return self.is_in_range(date_renouvellement_habit, ranges)
        
        elif date_renouvellement_loisir != '':
            return self.is_in_range(date_renouvellement_loisir, ranges)

        return False                
    
    
    def remove_double_by_phone(self, dates_autres, dates_intact):
        
        loader = Loader("Remove double by phone...", 'Done', 0.05).start()
        new_list = dates_intact.copy()
        
        for i in new_list:

            if any(i[3] in s for s in dates_autres) == True:

                dates_intact.remove(i)
                
        loader.stop()
        return dates_autres, dates_intact
                      
    
    def mix_lists(self, dates_intact, dates_autres, ratio):
        
        if len(dates_intact) != 0 :
        
            count_intact = round(len(dates_intact) * ratio)
            calcul = round(len(dates_autres) / count_intact)
            index = calcul

            for i in dates_intact[:count_intact]:
                dates_autres.insert(index, i)
                index += calcul

        return dates_autres
    
    
    def exist_in_genesys(self, genesys_list_numbers, phone):
        return phone in genesys_list_numbers
    
    
    def exist_in_sugar(self, s_list_numbers, phone):
        return phone in s_list_numbers


    def find_in_genesys_by_id(self, f_contacts, id):
        
        """Retourne le contact sugar s'il existe, sinon retourne None"""
        
        for f in f_contacts:
            if(id == f['custom']):
                return f

        return None


    def update_phone(self, s_contact, f_contacts, contact_list_id):

        f_contact = self.find_in_genesys_by_id(f_contacts, s_contact["id"])
        
        if(f_contact is not None and f_contact["number"] != s_contact["phone_home"]):
            
            self.outbound.update_a_contact(contact_list_id, s_contact["id"], {'data': {"number": s_contact["phone_home"]}} )


    def __create_to_genesys(self, s_contacts, contact_list_id):
        contacts_to_add = []
        
        for s_contact in s_contacts:   

            contacts_to_add.append({"id": s_contact["id"], 
                                    "data": {
                                        "number": s_contact["phone_home"], 
                                        "custom": s_contact["id"],
                                        "firstname": s_contact["first_name"], 
                                        "lastname": s_contact["last_name"], 
                                        "source_principale": s_contact["source_principale_c"], 
                                        "source_secondaire": s_contact["source_secondaire_c"],
                                        "nb_attempts": 0, 
                                        "nb_attempts_per_day": 0,
                                        "other_1": s_contact["salutation"],
                                        "other_2":"",
                                        "other_3":""  
                                    }
            })
       
        self.outbound.add_contacts_to_a_contact_list(contact_list_id, contacts_to_add)
    
    
    def __delete_of_genesys(self, f_contacts, contact_list_id):
        
        contacts_to_delete = []
        
        for f_contact in f_contacts:
            print(f_contact['custom'])
            contacts_to_delete.append(f_contact['custom'])
        
        print(len(contacts_to_delete)) 
        self.outbound.delete_contacts_from_a_contact_list(contact_list_id, contacts_to_delete)


    def __update_of_genesys(self, s_contacts, genesys_list, contact_list_id):
        
        for s_contact in s_contacts:
            
            self.update_phone(s_contact, genesys_list, contact_list_id)


    def update(self, s_contacts):
        self.file_logger.info(f"genesys Update Start")

        contact_list_id = self.outbound.get_contact_list_id_from_a_campaign_name(GenesysCampaign.C_VENDEUR_PARTICULIER)    
        genesys_list = self.outbound.get_all_contacts_from_a_contact_list(contact_list_id)        
        
        f_list_numbers =  list(map(lambda x: x['number'], genesys_list))
        s_list_numbers = list(map(lambda sc: sc["phone_home"] , s_contacts))

        s_to_create = list(filter(lambda s_c: not self.exist_in_genesys(f_list_numbers,s_c["phone_home"]),s_contacts ))
        s_to_update = list(filter(lambda s_c: self.exist_in_genesys(f_list_numbers,s_c["phone_home"]),s_contacts ))
        f_to_delete = list(filter(lambda f_c: not self.exist_in_sugar(s_list_numbers, f_c["number"] ), genesys_list))

        self.file_logger.info(f"Contacts ajoutés : {len(s_to_create)}")
        self.file_logger.info(f"Contacts modifiés : {len(s_to_update)}")
        self.file_logger.info(f"Contacts supprimés : {len(f_to_delete)}")
        
        #UPDATE
        print('create')
        self.__create_to_genesys(s_to_create, contact_list_id)
        print('update')
        self.__update_of_genesys(s_to_update, genesys_list, contact_list_id)
        print('delete')
        self.__delete_of_genesys(f_to_delete, contact_list_id)
        
        self.file_logger.info(f"Genesys Update Stop")




    def job(self):
        
        self.file_logger.info("VendeurParticulier JOB START")
        self.__init_api_client()
        
        # self.outbound.delete_all_contacts_from_a_contact_list("0eeeb25b-ef8b-4ca0-b4fe-929f9f193b8e")
        
        dates = list(zip(self.get_start_dates(), self.get_end_dates()))
        
        #Contacts 
        contacts_autres = LinksToContact(self.sac_client, self.dorm_client, 
            contacts_dicts=self.get_dates_autres() 
        ).filter(self.dates_are_in_ranges, args=tuple(dates))

        #Contacts Intacts
        contacts_intacts = LinksToContact(self.sac_client, self.dorm_client, 
            contacts_dicts=self.get_dates_intact() 
        ).filter(self.dates_are_in_ranges, args=tuple(dates))

        self.file_logger.info(f"Dates Intact : {len(contacts_intacts.ids)}")
        self.file_logger.info(f"Dates Autres : {len(contacts_autres.ids)}")
                        
        dates_finale = contacts_autres.mix_lists(contacts_intacts, self.ratio).to_dicts()
        
        self.file_logger.info(f"Dates : {len(dates_finale)}")
            
        self.update(dates_finale)
                        
 
 
        
class Service(ServiceSuper):
    
    NAME = 'g-vendeur-particulier'
    
    def __init__(self):
       
        ServiceSuper.__init__(self, Service.NAME)
        self.tag_vp = TagVendeurParticulier(self.file_logger)
        self.vp = VendeurParticulier(self.file_logger)
        self.dorm = DormApiClient()        

    
    def job(self):
        
        try:
            self.event_start(self.dorm, datetime.now())
            self.event_status(self.dorm, ServiceStatus.PENDING)

            self.tag_vp.job()
            self.vp.job()

            self.event_status(self.dorm, ServiceStatus.SUCESS)
            
        except Exception as e:
            
            self.file_logger.error(traceback.format_exc())
            self.event_status(self.dorm, ServiceStatus.FAILED)
            log_on_slack({"Jonathan": "UKXMF9952", 
                      }, 
                      f"Vendeur Particulier : Failed at -{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} with {e}")

        finally:
            
            self.send_log(self.dorm, True)
            self.event_end(self.dorm, datetime.now())


    def exec(self):
        
        self.file_logger.info('vendeur-particulier info')
        
        # LUNDI
        schedule.every().monday.at("01:10").do(self.job)

        # MARDI
        schedule.every().tuesday.at("01:10").do(self.job)

        # MERCREDI
        schedule.every().wednesday.at("01:10").do(self.job)

        # JEUDI
        schedule.every().thursday.at("01:10").do(self.job)

        # VENDREDI
        schedule.every().friday.at("01:10").do(self.job)

        while True:

            schedule.run_pending()
            time.sleep(1)  


if __name__ == '__main__': 

    start = Service()
    start.job()
    # start.exec()
    