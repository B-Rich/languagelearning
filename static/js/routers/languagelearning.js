/*jslint browser: true, nomen: true */
/*global define */

define([
    'underscore',
    'backbone',
    'jquery',
    'adapters/search',
    'views/searchBox',
    'views/expression'
], function (_, backbone, $, searchAdapter, SearchBoxView, ExpressionView) {
    "use strict";

    var $mainDiv = $('div.main-container div.main'),
        $horizon = $('div.horizon'),
        $header = $('div.header-container header');

    return backbone.Router.extend({
        routes: {
            "": "home",
            "expression/:expression": "expression"
        },

        initialize: function (options) {
            this._searchBoxView = new SearchBoxView({router: this}).render();
            this._expressionView = new ExpressionView({router: this}).render();
        },

        home: function () {
            $header.hide();
            this._searchBoxView.$el.detach().appendTo($horizon.show());
            this._expressionView.$el.detach();
        },

        expression: function (expression) {
            var self = this,
                loadingDfd,
                pathName = 'expression/' + encodeURIComponent(expression);

            this.navigate(pathName);

            $horizon.hide();
            this._searchBoxView.expression = expression;
            this._searchBoxView.render().$el.detach().appendTo($header.show());
            this._expressionView.$el.appendTo($mainDiv.show());
            loadingDfd = this._expressionView.loading();

            searchAdapter.search(expression).done(function (expressionModel) {
                self._expressionView.render(expressionModel);
            }).fail(function (expressionModel) {
                self._expressionView.render(expressionModel);
            }).always(function () {
                loadingDfd.resolve();
            });
        }
    });
});
