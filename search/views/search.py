
# Imports ###########################################################

import json
import os
import string

from nltk import word_tokenize, sent_tokenize
from pycaustic import Scraper

from django.conf import settings

from dist.bingsearch import BingSearchAPI
from dist.googletranslate import GoogleTranslator
from utils.api import APIView, ErrorResponse


# Classes ###########################################################

class SearchAPIView(APIView):
    
    def fetch_parameters(self, request):
        """
        Retreives query parameters from the request data
        """
        self.expression = request.GET.get(u'expression', u'')
        self.source = request.GET.get(u'source', u'').lower()
        self.target = request.GET.get(u'target', u'en').lower()
        self.query_types = request.GET.getlist(u'query_type', [])
        self.words = self.tokenize_words(self.expression)
        # TODO: key, callback

        # Query format check
        if not self.expression or not self.words:
            raise ErrorResponse(u"'expression' can't be empty")

    def progressive_get(self, request):
        self.fetch_parameters(request)
        if not self.query_types:
            raise ErrorResponse(u'No query type specified')
        
        results = {}
        # TODO better way to ensure 'translation' is run first, system of
        # dependencies for the different queries.
        for query_type in (u'translation', u'images', u'definitions'):
            if query_type in self.query_types:
                results[query_type] = getattr(self, u'query_{0}'.format(query_type))() 
                # TODO remove me: this can be uncommented to visually test
                # progressive loading in different browsers.
                # import time
                # time.sleep(1)
                yield {
                        u'expression': self.expression,
                        u'source': self.source,
                        u'target': self.target,
                        u'status': u'success',
                        u'results': results
                    }


    def handle_error(self, request, e):
        return self.render_to_response({
                u'expression': self.expression,
                u'source': self.source,
                u'target': self.target,
                u'status': u'error',
                u'error': e.description
            }, status=400)
    
    def query_translation(self):
        translator = GoogleTranslator()
        expression = self.expression.encode('utf8') # google translate lib expects a bytestring
        response = translator.translate(expression, source=self.source, target=self.target)

        if u'error' in response:
            # When Google can't translate between language pairs, still detect source & proceed
            if 'message' in response['error'] and \
                    response['error']['message'] == 'Bad language pair: {0}':
                source_response = translator.detect(expression)
                self.source = source_response['data']['detections'][0][0]['language']
                # Return the source text to mirror GT's behavior when it can't translate
                translated_text = self.expression
            else:
                raise ErrorResponse(json.dumps(response[u'error']))
        
        else:
            translation = response[u'data'][u'translations'][0]
            translated_text = translation[u'translatedText']

            if not self.source and u'detectedSourceLanguage' in translation:
                self.source = translation[u'detectedSourceLanguage']

        return translated_text

    def query_images(self):
        bing = BingSearchAPI(settings.BING_API_KEY)
        # use exact search
        expression = ' '.join([u'+{0}'.format(word) for word in self.words])
        # bing lib expects a bytestring
        expression = expression.encode('utf8')
        response = bing.search(u'image', expression, {
                u'$format': u'json',
                u'$top': 6,
                u'$skip': 0 
            })

        images = []
        for image in response[u'd'][u'results'][0][u'Image']:
            images.append({
                    u'url': image[u'Thumbnail'][u'MediaUrl'],
                    u'size': [image[u'Thumbnail'][u'Width'], image[u'Thumbnail'][u'Height']],
                    u'meta': { u'engine': u'bing images' }
                })

        return images

    def query_definitions(self):
        scraper = Scraper()
        if not self.source:
            # TODO not a huge fan of the self.source side-effect from this,
            # this requires the sorted() hack above to ensure that queries are
            # run in the correct order and avoid duplication.
            self.query_translation()
            if not self.source:
                return None # No source language, can't look up definition.

        try:
            instruction = json.load(open(os.path.join(settings.INSTRUCTIONS_DIR,
                                                      u'{0}.json'.format(self.source))))
        except IOError:
            # Language not supported, can't look up definition.
            return None
        else:
            definitions = []
            for word in self.words:
                definition = {
                    "word": word
                }

                resp = scraper.scrape(instruction,
                                      force=True,
                                      tags={u'word': word.encode('utf8')})
                if resp.flattened_values:
                    val = resp.flattened_values[u'definition']
                    if isinstance(val, list):
                        sentences = [v[u'definition'].decode('unicode-escape') for v in val]
                    else:
                        sentences = [val.decode('unicode-escape')]

                    definition['sentences'] = sentences

                definitions.append(definition)

            return definitions

        # No definitions found
        return None

    def tokenize_words(self, expression):
        """
        Returns a list of individual words contained in the expression, stripped of
        punctuation.
        """
        tokens = [token for sentence in sent_tokenize(expression) 
                        for token in word_tokenize(sentence)]
        words = filter(lambda token: token not in string.punctuation, tokens)
        return words

