import os
import sys
import tempfile
import unittest
from unittest import mock

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import geocodage


def _reponse(type_, score, cp="69007", lon=4.83, lat=45.73):
    r = mock.Mock()
    r.json.return_value = {"features": [{
        "properties": {"type": type_, "score": score, "postcode": cp},
        "geometry": {"coordinates": [lon, lat]},
    }]}
    return r


class GeocodageTest(unittest.TestCase):
    def setUp(self):
        self.cache = os.path.join(tempfile.mkdtemp(), "cache.json")
        geocodage._cache = None  # cache mémoire du module isolé entre tests

    def _geocoder(self, adresse="52 rue André Bollier", get=None, **kw):
        with mock.patch.object(geocodage.requests, "get", get):
            return geocodage.geocoder(adresse, cache_path=self.cache, **kw)

    def test_numero_trouve(self):
        res = self._geocoder(get=mock.Mock(return_value=_reponse("housenumber", 0.83)))
        self.assertEqual(res, {"lat": 45.73, "lon": 4.83, "precision": "numero", "cp": "69007"})

    def test_rue_seule_donne_precision_rue(self):
        res = self._geocoder(get=mock.Mock(return_value=_reponse("street", 0.82)))
        self.assertEqual(res["precision"], "rue")

    def test_score_faible_ou_type_vague_rejetes(self):
        self.assertIsNone(self._geocoder(get=mock.Mock(return_value=_reponse("housenumber", 0.5))))
        self.assertIsNone(self._geocoder("rue X", get=mock.Mock(return_value=_reponse("municipality", 0.99))))

    def test_une_adresse_un_appel_meme_sans_resultat(self):
        get = mock.Mock(return_value=mock.Mock(json=lambda: {"features": []}))
        self.assertIsNone(self._geocoder(get=get))
        self.assertIsNone(self._geocoder(get=get))
        self.assertEqual(get.call_count, 1)

    def test_cache_relu_depuis_le_disque(self):
        self._geocoder(get=mock.Mock(return_value=_reponse("housenumber", 0.9)))
        geocodage._cache = None
        get = mock.Mock(side_effect=AssertionError("réseau appelé"))
        self.assertEqual(self._geocoder(get=get)["precision"], "numero")

    def test_erreur_reseau_none_retry_et_pas_de_cache(self):
        get = mock.Mock(side_effect=requests.ConnectionError("hors ligne"))
        self.assertIsNone(self._geocoder(get=get))
        self.assertEqual(get.call_count, geocodage.ESSAIS)
        self.assertFalse(os.path.exists(self.cache))
        # le réseau revient : l'adresse est retentée
        self.assertIsNotNone(self._geocoder(get=mock.Mock(return_value=_reponse("street", 0.9))))

    def test_postcode_transmis_et_dans_la_cle_de_cache(self):
        get = mock.Mock(return_value=_reponse("street", 0.9))
        self._geocoder(get=get, postcode="69007")
        self.assertEqual(get.call_args.kwargs["params"]["postcode"], "69007")
        self.assertEqual(get.call_args.kwargs["params"]["citycode"], geocodage.CITYCODE_LYON)


if __name__ == "__main__":
    unittest.main()
