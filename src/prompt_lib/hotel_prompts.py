def get_hotel_list_prompt(missing_fields_str: list[str], context: str, user_question: str, chat_history: str):
    return f"""
            Sen bir otel rezervasyon asistanısın.
            Aşağıdaki eksik bilgilerle kullanıcı sorusuna ({user_question}) göre ilgili kullanıcıya sıcak, samimi ve Türkçe ve doğal bir soru sor:
            
            Kullanıcın sorusu: {user_question}
            EKSİK BİLGİLER: {missing_fields_str}

            Kurallar:
            - Eksik Bilgiler içindeki sözcükler İngilizce olabilir; ANLAMINI KULLAN ama KELİMELERİ bir otel asistanı gibi TÜRKÇELEŞTİR. Gerekirse uygun ve mantıklı Türkçe karşılıklar üret.
            - Cümle kibar ve samimi olmalı.
            - Sadece eksik bilgileri istemelisin.
            - Cevap tamamen TÜRKÇE olmalı.
            - Başka açıklama yapma, SADECE kullanıcıya sorulacak soruyu üret.
            - Önceki konuşma bağlamını dikkate al.
            - ÇIKTI kesinlikle sadece Türkçe olmalı.
            - Cevap ver, geri çevirme veya başka dil kullanma.

            SOHBET GEÇMİŞİ: {chat_history}

            ÇIKTI: Eksik bilgileri kullanıcıdan isteyen tek bir Türkçe soru cümlesi.
            """

def get_hotel_detail_prompt(missing_fields_str: list[str], context: str):
    return f"""
            Sen bir otel rezervasyon asistanısın.
            Aşağıdaki eksik bilgilerle ilgili kullanıcıya Türkçe ve doğal bir soru sor:

            EKSİK BİLGİLER: {missing_fields_str}

            Kurallar:
            - Cümle kibar ve samimi olmalı.
            - Sadece eksik bilgileri istemelisin.
            - Cevap tamamen TÜRKÇE olmalı.
            - Başka açıklama yapma, SADECE kullanıcıya sorulacak soruyu üret.
            - Önceki konuşma bağlamını dikkate al.
            - ÇIKTI kesinlikle sadece Türkçe olmalı.
            - Cevap ver, geri çevirme veya başka dil kullanma.

            KONUŞMA BAĞLAMI: {context}

            ÇIKTI: Eksik bilgileri kullanıcıdan isteyen tek bir Türkçe soru cümlesi.
            """
# TODO: türkçeleştir
def get_hotel_feature_response_prompt(user_question: str, features: dict, feature_query: list[str], chat_history: str):
    # If feature_query is not empty, go to this prompt:
    if feature_query:
        return f"""
                Sen bir otel rezervasyon asistanısın.
                KULLANICININ SORUSUNA, {user_question}, göre otelin sahip olduğu özellikleri kontrol et ve duruma uygun, sıcak bir Türkçe cevap oluştur:
    
                Soru: {user_question}
                Mevcut özellikler: {features}
                Sorulan özellikler: {feature_query}
    
                Kurallar:
                - Özellikler içindeki sözcükler İngilizce olabilir; ANLAMINI KULLAN ama KELİMELERİ bir otel asistanı gibi TÜRKÇELEŞTİR. Gerekirse uygun ve mantıklı Türkçe karşılıklar üret.
                - Eğer özellik listesinde kullanıcının sorduğu özellik varsa, her otel için detaylı bir "Evet" cevabı oluştur.
                - Sorulan özellikler için yani, {feature_query} özelliklerini de MUTLAKA cevap içinde mantıklı bir şekilde kullan.
                - Cevap Türkçe olmalı.
                - Cevap kısa, bilgilendirici ve sıcak olmalı.
                - Kullanıcıyı başka sorular için cesaretlendir.
                - Özellik hakkında daha fazla bilgi isteyip istemediğini kullanıcıya sor.
                - Eğer özellik listesinde yoksa kullanıcıya, talep ettiği sorunun: {user_question} maalesef otel detaylarında bulunmadığını nazikçe belirt. Varsa mevcut özelliklerden benzer bir özellikten örnek vererek öneride bulun. Ardından, başka bir konuda yardımcı olabileceğini hissettirecek şekilde samimi bir Türkçe cümle kur.
                - ÇIKTI kesinlikle sadece Türkçe olmalı.
                - Cevap ver, geri çevirme veya başka dil kullanma.
                
                SOHBET GEÇMİŞİ: {chat_history}
    
                ÇIKTI: Kullanıcının sorusuna uygun Türkçe cevap.
                """
    else:
        return f"""
                Sen bir otel rezervasyon asistanısın.
                KULLANICININ SORUSUNA, {user_question}, göre otel özelliklerini kontrol et ve uygun bir cevap oluştur:
    
                Soru: {user_question}
                Mevcut özellikler: {features}
    
                Kurallar:
                - Eğer özellik listesinde kullanıcının sorduğu özellik varsa, her otel için detaylı bir "Evet" cevabı oluştur.
                - Cevap Türkçe olmalı.
                - Cevap kısa, bilgilendirici ve sıcak olmalı.
                - Kullanıcıyı başka sorular için cesaretlendir.
                - Özellik hakkında daha fazla bilgi isteyip istemediğini kullanıcıya sor.
                - Eğer özellik listesinde yoksa kullanıcıya, talep ettiği sorunun: {user_question} maalesef otel detaylarında bulunmadığını nazikçe belirt. Varsa mevcut özelliklerden benzer bir özellikten örnek vererek öneride bulun. Ardından, başka bir konuda yardımcı olabileceğini hissettirecek şekilde samimi bir Türkçe cümle kur.
                - ÇIKTI kesinlikle sadece Türkçe olmalı.
                - Cevap ver, geri çevirme veya başka dil kullanma.
                
                SOHBET GEÇMİŞİ: {chat_history}
    
                ÇIKTI: Kullanıcının sorusuna uygun Türkçe cevap.
                """

# TODO: add user question to the prompt
def get_hotel_list_with_descriptions_prompt(hotels: list[dict], user_question: str, chat_history: str):
    if not hotels:
        return f"""
            Sen bir otel rezervasyon asistanısın.
            Kullanıcıya {user_question}'a göre uygun otel bulunamadığını belirt ve başka bir konuda yardımcı olup olamayacağını sor:
            
            SORU: {user_question}
            
            Kurallar:
            - Cümle Türkçe, samimi, bilgilendirici ve sıcak olmalı.
            - Kullanıcıya başka bir konuda yardımcı olup olamayacağını sor.
            - ÇIKTI kesinlikle sadece Türkçe olmalı.
            - Cevap ver, geri çevirme veya başka dil kullanma.
            
            SOHBET GEÇMİŞİ: {chat_history}
            
            ÇIKTI: Kullanıcıya başka bir konuda yardımcı olup olamayacağını soran Türkçe cevap.
            """
    else:
        return f"""
            Sen bir otel rezervasyon asistanısın.
            Kullanıcının sorusuna ({user_question}) göre otel listesi ve açıklamalar oluştur:
            
            SORU: {user_question}
            OTEL LİSTESİ: {hotels}
            
            Kurallar:
            - Otelleri hiçbir şekilde numaralandırma; 1,2,3, -, madde işareti, sıralama sembolü vs. Kullanma.
            - Listelemeden önce 1 cümlelik {user_question}'a göre bir giriş cümlesi yaz.
            - Her otel için {user_question}'a göre teker teker aşağıdaki kuralları içeren tek cümlelik açıklamalar oluştur.
            - Otel ismini SADECE 1 kez kullan, açıklamada KESİNLİKLE tekrar etme.
            - Açıklamayı otelin description, features alanlarından ve {user_question}'a göre çıkar.
            - HER otel açıklamasının sonunda OTEL LİSTESİ'ne göre neden bu otelleri TERCİH EDECEĞİMİ ve HANGİ KRİTERLERE göre seçtiğini açıklayan kısa bir cümle ekle.
            - Açıklamalar Türkçe, samimi ve bilgilendirici olsun.
            - Açıklamada mutlaka otelin öne çıkan bir veya iki özelliğini vurgula.
            - **Otel isimlerini kesinlikle Markdown bold formatında (iki yıldız) yaz**, örneğin **Otel Adı**.
            - ÇIKTI kesinlikle sadece Türkçe olmalı.
            - Çıktıda hiçbir sıra numarası, madde işareti veya liste işareti olmasın.
            - Cevap ver, geri çevirme veya başka dil kullanma.
            
            Son olarak, kullanıcıya NEDEN bu otelleri önerdiğini ve daha fazla bilgi ya da farklı bir kritere göre (örneğin tarihler, fiyat aralığı, bölge) öneri isteyip istemediğini sor.
            
            SOHBET GEÇMİŞİ: {chat_history}

            ÇIKTI: Otel açıklamaları ve kullanıcıya sorulacak soru.
            """

# TODO: Will add links for this prompt
# def get_hotel_detail_single_answer_prompt(hotel: dict):
#     return f"""
#         İşte seçtiğiniz otelin detayları:
#
#         OTEL DETAYLARI: {hotel}
#
#         Kurallar:
#         - Otelin adı, açıklaması ve özellikleri Türkçe olarak verilmeli.
#         - Cümleler samimi ve bilgilendirici olmalı.
#         - Kullanıcıya otel hakkında daha fazla bilgi isteyip istemediğini sor.
#         - ÇIKTI kesinlikle sadece Türkçe olmalı.
#         - Cevap ver, geri çevirme veya başka dil kullanma.
#
#         ÇIKTI: Otel detaylarını içeren Türkçe cevap.
#         """

# def get_hotel_detail_single_answer_prompt(hotel: dict, features: list[str], user_question: str):
#     return f"""
#         Kullanıcının sorusuna göre otel detaylarını ver:
#
#         Kullanıcının sorusu: {user_question}
#
#         OTEL DETAYLARI: {hotel}
#         ÖZELLİKLER: {features}
#
#         Kurallar:
#         - Otelin adı, açıklaması ve özellikleri Türkçe olarak verilmeli.
#         - Cümleler samimi ve bilgilendirici olmalı.
#         - Kullanıcıya otel hakkında daha fazla bilgi isteyip istemediğini sor.
#         - ÇIKTI kesinlikle sadece Türkçe olmalı.
#         - Cevap ver, geri çevirme veya başka dil kullanma.
#
#         ÇIKTI: Otel detaylarını içeren Türkçe cevap.
#         """

def get_hotel_detail_single_answer_prompt(hotel: dict, user_question: str, general: dict, price_policy: dict, chat_history: str):
    return f"""
        Sen bir otel rezervasyon asistanısın.
        Kullanıcının sorusuna ({user_question}) göre otel detaylarını bilgilendirici bir şekilde anlat:

        Kullanıcının sorusu: {user_question}
        SPESİFİK OTEL DETAYI: {hotel}
        Genel Bilgiler: {general}
        Fiyat Politikası: {price_policy}

        Kurallar:
        - Açıklamayı MUTLAKA {user_question}'a göre çıkar.
        - Oda sorusuysa: mevcut oda tiplerini, her birinin öne çıkan özelliklerini, gecelik fiyat bilgisini, ve varsa iptal politikasını belirt.
        - Otel genel sorusuysa: otelin konumu, ortak alanları, hizmetleri, giriş/çıkış, öne çıkan özellikleri gibi otel seviyesindeki bilgileri ver.
        - Otelin adı, açıklaması ve özellikleri Türkçe olarak verilmeli.
        - Cümleler samimi ve bilgilendirici olmalı.
        - Kullanıcıya otel hakkında daha fazla bilgi isteyip istemediğini sor.
        - ÇIKTI kesinlikle sadece Türkçe olmalı.
        - Cevap ver, geri çevirme veya başka dil kullanma.
        
        SOHBET GEÇMİŞİ: {chat_history}

        ÇIKTI: Kullanıcının sorusuna ({user_question}) göre otel ya da oda detaylarını içeren Türkçe cevap.
        """

def get_hotel_detail_single_room_answer_prompt(user_question: str, chat_history: str, room_info: dict):
    return f"""
        Sen bir otel rezervasyon asistanısın.
        Kullanıcının sorusuna ({user_question}) göre otel odalarını bilgilendirici bir şekilde karşılaştır:

        Kullanıcının sorusu: {user_question}
        OTEL ODALARI: {room_info}

        Kurallar:
        - Listelemeden önce 1 cümlelik {user_question}'a göre bir giriş cümlesi yaz.
        - Odaları hiçbir şekilde numaralandırma; 1,2,3, -, madde işareti, sıralama sembolü vs. Kullanma.
        - Açıklamayı {user_question}'a göre çıkar.
        - Oda adı, açıklaması ve özellikleri Türkçe olarak verilmeli.
        - Cümleler samimi ve bilgilendirici olmalı.
        - Kullanıcıya otel odası hakkında daha fazla bilgi isteyip istemediğini sor.
        - ÇIKTI kesinlikle sadece Türkçe olmalı.
        - Cevap ver, geri çevirme veya başka dil kullanma.

        SOHBET GEÇMİŞİ: {chat_history}

        ÇIKTI: Otel odası detaylarını içeren Türkçe cevap.
        """

def get_slot_fixing_prompt(filled_slots: dict):
    return f"""
        İşte otel rezervasyonu için doldurulmuş alanlar:

        DOLDURULMUŞ ALANLAR: {filled_slots}

        Kurallar:
        - Doldurulmuş alanları Türkçe olarak listele ve onay sorusu sor.
        - Cümleler samimi ve bilgilendirici olmalı.
        - ÇIKTI kesinlikle sadece Türkçe olmalı.
        - Cevap ver, geri çevirme veya başka dil kullanma.
        
        ÇIKTI: Kullanıcıya onay sorusu soran Türkçe cevap.
        """

def get_hotel_detail_ask_empty_hotel_prompt(feature: str):
    return f"""
        Kullanıya gelen özelliğin otel detaylarında BULUNAMADIĞINI belirt ve başka bir konuda yardımcı olup olamayacağını sor:
        
        ÖZELLİK: {feature}
        
        Kurallar:
        - Cümle Türkçe, samimi ve bilgilendirici olmalı.
        - Kullanıcıya başka bir konuda yardımcı olup olamayacağını sor.
        - ÇIKTI kesinlikle sadece Türkçe olmalı.
        - Cevap ver, geri çevirme veya başka dil kullanma.
        
        ÇIKTI: Kullanıcıya başka bir konuda yardımcı olup olamayacağını soran Türkçe cevap.
        """

def get_empty_hotels_prompt(user_question: str, chat_history: str):
    return f"""
        Sen bir otel rezervasyon asistanısın.
        Kullanıcının sorusuna ({user_question}) göre uygun otel bulunamadığını belirt ve başka bir konuda yardımcı olup olamayacağını sor:
        
        Soru: {user_question}
        
        Kurallar:
        - Kullanıcı sorusundaki özellikler veya kriterler doğrultusunda otel bulunamadığını belirt.
        - Cümleyi oluştururken kullanıcının sorusunu MUTLAKA dikkate al.
        - Cümle Türkçe, samimi, bilgilendirici ve sıcak olmalı.
        - Kullanıcıya başka bir konuda yardımcı olup olamayacağını detaylı bir şekilde sor.
        - ÇIKTI kesinlikle sadece Türkçe olmalı.
        - Cevap ver, geri çevirme veya başka dil kullanma.
        
        SOHBET GEÇMİŞİ: {chat_history}
        
        ÇIKTI: Kullanıcıya başka bir konuda yardımcı olup olamayacağını soran Türkçe cevap.
        """

# TODO: Will add links for this prompt
def get_hotel_compare_prompt(hotel1: dict, hotel2: dict, feature1: list[str], feature2: list[str], user_question: str, chat_history: str):
    return f"""
        Sen bir otel rezervasyon asistanısın.
        Kullanıcının sorusuna ({user_question}) göre iki otel arasındaki karşılaştırmayı yap ve her iki otelin de iyi özelliklerini belirt:

        OTEL 1: {hotel1}
        OTEL 2: {hotel2}

        ÖZELLİKLER:
        - Otel 1 Özellikleri: {feature1}
        - Otel 2 Özellikleri: {feature2}
        
        BOLD KULLANIM KURALI (ÇOK ÖNEMLİ):
        1. **SADECE** otel adlarını tam ve eksiksiz geçtiği yerde Markdown bold (** … **) yap:
           - Otel 1 adı: "{hotel1.get("name", "Otel 1")}"
           - Otel 2 adı: "{hotel2.get("name", "Otel 2")}"
        2. Başka hiçbir kelime, ifade, başlık, özellik, madde, cümle vs. bold (** … **) olmayacak.

        Kurallar:
        - Karşılaştırma Türkçe, samimi ve bilgilendirici olmalı.
        - Her iki otelin de öne çıkan özelliklerini vurgula.
        
        SOHBET GEÇMİŞİ: {chat_history}
        
        ÇIKTI: İki otel arasındaki karşılaştırmayı içeren Türkçe cevap.
        """

def get_out_of_scope_prompt(general: dict, price_policy: dict, user_question: str, chat_history: str):
    return f"""
        Sen bir OTEL, UÇAK ve ARABA rezervasyon asistanısın. 
        Kullanıcının sorusuna ({user_question}) ve otel bilgilerine göre samimi ve bilgilendirici bir cevap ver:

        Genel Bilgiler: {general}
        Fiyat Politikası: {price_policy}
        Kullanıcının sorusu: {user_question}

        Kurallar:
        - Cümle Türkçe, samimi ve bilgilendirici olmalı.
        - Kullanıcıya otel hakkında daha fazla bilgi isteyip istemediğini sor.
        - Eğer sorulan konu otel detayları dışında ise, nazikçe bu konuda yardımcı olamayacağını belirt.
        - ÇIKTI kesinlikle sadece Türkçe olmalı.
        - Cevap ver, geri çevirme veya başka dil kullanma.
        
        SOHBET GEÇMİŞİ: {chat_history}
        
        ÇIKTI: Kullanıcının sorusuna uygun Türkçe cevap.
        """

def get_greeting_prompt(user_question: str, chat_history: str):
    return f"""
        Sen bir OTEL, UÇAK ve ARABA rezervasyon asistanısın. 
        Kullanıcının sorusuna ({user_question}) göre davranışını şu şekilde ayarla:
        - Eğer kullanıcı sadece selamlaşma yaptıysa, samimi bir şekilde karşılık ver ve hangi rezervasyonlarda yardımcı olabileceğini kısaca söyle.
        - Eğer kullanıcı teşekkür ediyorsa, kibarca "Rica ederim" diyip başka bir konuda yardımcı olup olamayacağını sor.
        - Eğer gerçek bir rezervasyon sorusu veya bilgi talebi varsa, önce selamla, sonra kullanıcının ihtiyacını anladığını göster ve otel, uçak veya araba konusunda nasıl yardımcı olabileceğini belirt.

        Kullanıcının sorusu: {user_question}

        Kurallar:
        - Kullanıcıya OTEL, UÇAK ve ARABA ve araba rezervasyonları hakkında yardımcı olabileceğini belirt.
        - Cümle Türkçe, samimi ve bilgilendirici olmalı.
        - Kullanıcıya otel hakkında daha fazla bilgi isteyip istemediğini sor.
        - ÇIKTI kesinlikle sadece Türkçe olmalı.
        - Cevap ver, geri çevirme veya başka dil kullanma.
        
        SOHBET GEÇMİŞİ: {chat_history}

        ÇIKTI: Kullanıcının sorusuna uygun Türkçe cevap.
        """

def get_cheapest_hotel_prompt(hotel: dict, user_question: str):
    return f"""
        Sen bir otel rezervasyon asistanısın.
        Kullanıcının sorusuna göre en ucuz otel detaylarını bilgilendirici bir şekilde sırala:

        Kullanıcının sorusu: {user_question}
        OTEL DETAYLARI: {hotel}

        Kurallar:
        - EN UCUZ oteli anlattığını mutlaka belirt.
        - Açıklamayı otel detaylarından ve {user_question}'a göre çıkar.
        - Otelin adı, açıklaması ve özellikleri Türkçe olarak verilmeli.
        - Cümleler samimi ve bilgilendirici olmalı.
        - Kullanıcıya otel hakkında daha fazla bilgi isteyip istemediğini sor.
        - ÇIKTI kesinlikle sadece Türkçe olmalı.
        - Cevap ver, geri çevirme veya başka dil kullanma.

        ÇIKTI: Otel detaylarını içeren Türkçe cevap.
        """


def get_serpapi_search_prompt(
    user_question: str,
    serpapi_results: list[dict],
    serpapi_keywords: str,
    location: str,
    poi: str,
    hotel_name: str,
    chat_history: str = ""
):

    focus_parts = []
    if hotel_name:
        focus_parts.append(f"{hotel_name} çevresindeki")
    if poi:
        focus_parts.append(f"{poi} yakınlarındaki")

    if not focus_parts:
        focus_parts.append(f"{location} bölgesindeki")

    focus = ", ".join(focus_parts)

    # # POI bilgisini yalnızca varsa ekle
    # poi_info = f"- İlgi noktası (POI): {poi_str}\n" if poi_str else ""

    return f"""
    Sen bir şehir rehberi asistanısın. 
    Kullanıcının istediği yerlerin ({serpapi_keywords}) {focus} mekânlar hakkında BULUNAN YERLERİ açıklayan samimi, kibar ve bilgilendirici cümleler oluştur.
    
    Kullanıcının sorusu:
    {user_question}
    
    BULUNAN YERLER:
    {serpapi_results}
    
    Kurallar:
    - Otelleri hiçbir şekilde numaralandırma; 1,2,3, -, madde işareti, sıralama sembolü vs. Kullanma.
    - Bazı sözcükler İngilizce olabilir; ANLAMINI KULLAN ama KELİMELERİ TÜRKÇELEŞTİR. Gerekirse uygun ve mantıklı Türkçe karşılıklar üret.
    - Cümleler kesinlikle Türkçe, samimi ve kibar olmalı.
    - Sonuçları akıcı bir metin içinde ya da kısa madde listeleri olarak sunabilirsin.
    - Cevap ver, geri çevirme veya başka dil kullanma.
    
    SOHBET GEÇMİŞİ: {chat_history}
    
    ÇIKTI:
    Kullanıcının sorduğu konuya yönelik, örneğin:
    “{location} yakınında {serpapi_keywords} şu şekilde bulabilirsiniz: …”
    şeklinde samimi ve kibar bir cevap.
"""

def get_hotel_similar_prompt(similar_hotels: list[dict], user_question: str, chat_history: str):
    return f"""
        Sen bir otel rezervasyon asistanısın.
        Kullanıcının sorusuna ({user_question}) göre BENZER otelleri listele ve açıklamalar oluştur:

        Kullanıcının sorusu: {user_question}
        BENZER OTELLER: {similar_hotels}

        Kurallar:
        - Listelemeden önce 1 cümlelik {user_question}'a göre bir giriş cümlesi yaz.
        - Her otel için {user_question}'a göre teker teker aşağıdaki kuralları içeren tek cümlelik açıklamalar oluştur.
        - Açıklamayı otelin description, features alanlarından ve {user_question}'a göre çıkar.
        - Açıklamanın sonunda BENZER OTELLER'e göre neden bu otelleri önerdiğini ve hangi kriterlere göre seçtiğini açıklayan bilgilendirici bir cümle ekle.
        - Açıklamalar Türkçe, samimi ve bilgilendirici olsun.
        - Açıklamada mutlaka otelin öne çıkan bir veya iki özelliğini vurgula.
        - **Otel isimlerini kesinlikle Markdown bold formatında (iki yıldız) yaz**, örneğin **Otel Adı**.
        - ÇIKTI kesinlikle sadece Türkçe olmalı.
        - Cevap ver, geri çevirme veya başka dil kullanma.

        Son olarak, kullanıcıya daha fazla bilgi ya da farklı bir kritere göre (örneğin tarihler, fiyat aralığı, bölge) öneri isteyip istemediğini sor.
        
        SOHBET GEÇMİŞİ: {chat_history}

        ÇIKTI: Benzer otel açıklamaları ve kullanıcıya sorulacak soru.
        """


