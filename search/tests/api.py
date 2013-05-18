# -*- coding: utf8 -*-

# Imports ###########################################################

import json
import logging

from mock import Mock, call, patch

from django.conf import settings
from django.test import TestCase


# Classes ###########################################################

class APITest(TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

        # Local configuration shouldn't change test results
        settings.DEBUG = True

    def api_check(self, response, status_code, reference):
        """
        Compare the JSON content of the response with a reference object, must be equal
        """
        self.assertEqual(response.status_code, status_code, response.content)
        response_obj = json.loads(response.content)
        try:
            self.assertEqual(response_obj, reference)
        except AssertionError:
            expected = json.dumps(reference, indent=2, sort_keys=True)
            message = u'\nReturned:\n{returned}\n\nExpected:\n{expected}'.format(returned=response.content,
                                                                                 expected=expected)
            raise AssertionError(message)


class SearchAPITest(APITest):

    def test_api_search_missing_parameters_expression(self):
        response = self.client.get(u'/api/v1/search')
        self.api_check(response, 400, {
                u'error': u"'expression' can't be empty",
                u'expression': u'', 
                u'source': u'', 
                u'status': u'error', 
                u'target': u'en'
            })
        
    def test_api_search_missing_parameters_expression_empty(self):
        response = self.client.get(u'/api/v1/search?expression=')
        self.api_check(response, 400, {
                u'error': u"'expression' can't be empty", 
                u'expression': u'', 
                u'source': u'', 
                u'status': u'error', 
                u'target': u'en'
            })
        
    def test_api_search_missing_parameters(self):
        response = self.client.get(u'/api/v1/search?expression=test')
        self.api_check(response, 400, {
                u'error': u'No query type specified', 
                u'expression': u'test', 
                u'source': u'', 
                u'status': u'error', 
                u'target': u'en'
            })

    def set_mock_translate(self, MockGoogleTranslator, mock_translate):
        # Mock class instance
        mock_translator = Mock()
        def create_mock_translator():
            return mock_translator
        MockGoogleTranslator.side_effect = create_mock_translator
        
        mock_translator.translate.side_effect = mock_translate
        return mock_translator

    @patch('search.views.search.GoogleTranslator')
    def test_api_search_translation(self, MockGoogleTranslator):
        # Predetermine translation results
        def mock_translate(*args, **kwargs):
            return {
                    u'data': {
                        u'translations': [{
                            u'translatedText': u'good day eèÉɘ',
                            u'detectedSourceLanguage': u'pt'
                        }]
                    }
                }
        mock_translator = self.set_mock_translate(MockGoogleTranslator, mock_translate)

        response = self.client.get(u'/api/v1/search?expression=bom%20dia%20e%C3%A8%C3%89%C9%98&query_type=translation')
        self.api_check(response, 200, {
                u'expression': u'bom dia eèÉɘ',
                u'results': {
                    u'translation': u'good day eèÉɘ'
                }, 
                u'source': u'pt', 
                u'status': u'success', 
                u'target': u'en'
            })
        self.assertEqual(mock_translator.mock_calls, [call.translate('bom dia e\xc3\xa8\xc3\x89\xc9\x98', source=u'', target=u'en')])
        
    @patch('search.views.search.GoogleTranslator._fetch_data')
    def test_api_search_translation_innermock(self, mock_fetch_data):
        """
        Only mock the actual fetching of data, to allow to catch unicode processing errors
        from googletranslate lib
        """
        def mock_fetch_data_side_effect(*args, **kwargs):
            return json.dumps({
                    u'data': {
                        u'translations': [{
                            u'translatedText': u'good day eèÉɘ',
                            u'detectedSourceLanguage': u'pt'
                        }]
                    }
                })
        mock_fetch_data.side_effect = mock_fetch_data_side_effect

        response = self.client.get(u'/api/v1/search?expression=bom%20dia%20e%C3%A8%C3%89%C9%98&query_type=translation')
        self.api_check(response, 200, {
                u'expression': u'bom dia eèÉɘ',
                u'results': {
                    u'translation': u'good day eèÉɘ'
                }, 
                u'source': u'pt', 
                u'status': u'success', 
                u'target': u'en'
            })

    @patch('search.views.search.GoogleTranslator')
    def test_api_search_translation_error_message(self, MockGoogleTranslator):
        """
        Translation returns an error message
        """
        def mock_translate(*args, **kwargs):
            return {u'error': [u'Error message']}
        self.set_mock_translate(MockGoogleTranslator, mock_translate)

        response = self.client.get(u'/api/v1/search?expression=bom%20dia%20e%C3%A8%C3%89%C9%98&query_type=translation')
        self.api_check(response, 400, {
                u'error': u'["Error message"]',
                u'expression': u'bom dia eèÉɘ', 
                u'source': u'', 
                u'status': u'error', 
                u'target': u'en'
            })
        
    @patch('search.views.search.GoogleTranslator')
    def test_api_search_translation_error_unexpected_format(self, MockGoogleTranslator):
        """
        Translation returns an unexpected format
        """
        def mock_translate(*args, **kwargs):
            return {u'something': u'unexpected'}
        self.set_mock_translate(MockGoogleTranslator, mock_translate)

        settings.DEBUG = False
        response = self.client.get(u'/api/v1/search?expression=bom%20dia%20e%C3%A8%C3%89%C9%98&query_type=translation')
        self.api_check(response, 400, {
                u'error': u'Sorry! An error has occurred.',
                u'expression': u'bom dia eèÉɘ', 
                u'source': u'', 
                u'status': u'error', 
                u'target': u'en'
            })
        
    @patch('search.views.search.GoogleTranslator')
    def test_api_search_translation_error_exception_debug_off(self, MockGoogleTranslator):
        """
        Translation throws an exception, with debug off
        """
        def mock_translate(*args, **kwargs):
            raise KeyError(u'test error one')
        self.set_mock_translate(MockGoogleTranslator, mock_translate)

        settings.DEBUG = False
        response = self.client.get(u'/api/v1/search?expression=bom%20dia%20e%C3%A8%C3%89%C9%98&query_type=translation')
        self.api_check(response, 400, {
                u'error': u'Sorry! An error has occurred.',
                u'expression': u'bom dia eèÉɘ', 
                u'source': u'', 
                u'status': u'error', 
                u'target': u'en'
            })
       
    @patch('search.views.search.GoogleTranslator')
    def test_api_search_translation_error_exception_debug_on(self, MockGoogleTranslator):
        """
        Translation throws an exception, with debug on
        When debug is on, send back the exception description with the API answer
        """
        def mock_translate(*args, **kwargs):
            raise KeyError(u'test error one')
        self.set_mock_translate(MockGoogleTranslator, mock_translate)

        settings.DEBUG = True
        self.assertRaises(KeyError, 
                          self.client.get, 
                          u'/api/v1/search?expression=bom%20dia%20e%C3%A8%C3%89%C9%98&query_type=translation')

    def set_mock_images_search(self, MockBingSearchAPI, mock_search):
        # Mock class instance
        mock_bing = Mock()
        def create_mock_bing(*args, **kwargs):
            return mock_bing
        MockBingSearchAPI.side_effect = create_mock_bing
        
        mock_bing.search.side_effect = mock_search
        return mock_bing

    @patch('search.views.search.BingSearchAPI')
    def test_api_search_images(self, MockBingSearchAPI):
        # Predetermine translation results
        def mock_search(*args, **kwargs):
            return { u'd': { u'results': [{ u'Image': [{
                u'Thumbnail': {
                    u'MediaUrl': u'http://ts2.mm.bing.net/th?id=H.4742791658736641&pid=15.1',
                    u'Height': u'300',
                    u'Width': u'194',
                    u'FileSize': u'14554'
                }}]}]}}
        mock_bing = self.set_mock_images_search(MockBingSearchAPI, mock_search)

        response = self.client.get(u'/api/v1/search?expression=bom%20dia%20e%C3%A8%C3%89%C9%98&query_type=images')
        self.api_check(response, 200, {
                u'expression': u'bom dia eèÉɘ',
                u'results': {
                    u'images': [{
                        u'meta': {
                          u'engine': u'bing images'
                        }, 
                        u'size': [
                          u'194', 
                          u'300'
                        ], 
                        u'url': u'http://ts2.mm.bing.net/th?id=H.4742791658736641&pid=15.1'
                    }],
                }, 
                u'source': u'',
                u'status': u'success', 
                u'target': u'en'
            })
        self.assertEqual(mock_bing.mock_calls, [
                call.search('image', '+bom +dia +e\xc3\xa8\xc3\x89\xc9\x98', {
                        '$format': 'json',
                        '$top': 10,
                        '$skip': 0 
                    })
            ])
        
        
