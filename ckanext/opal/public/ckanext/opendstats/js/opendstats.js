// Initialize the echarts instance based on the prepared dom
"use strict";
this.ckan.module('opendstats', function($){
    return {
        initialize: function() {
            console.log("I've been initialized for element: ", this.el)
        }
    }
});

this.ckan.module('opendstats-toptag-charts', function($){
    return {
        initialize: function() {
            var chart = echarts.init(this.el[0])
            var option = {
                tooltip: {},
                series: [ {
                    type: 'wordCloud',
                    gridSize: 2,
                    sizeRange: [12, 50],
                    rotationRange: [-90, 90],
                    shape: 'pentagon',
                    width: 600,
                    height: 400,
                    drawOutOfBound: true,
                    textStyle: {
                        color: function () {
                            return 'rgb(' + [
                                Math.round(Math.random() * 160),
                                Math.round(Math.random() * 160),
                                Math.round(Math.random() * 160)
                            ].join(',') + ')';
                        }
                    },
                    emphasis: {
                        textStyle: {
                            shadowBlur: 10,
                            shadowColor: '#333'
                        }
                    },
                    data: data_tag
                } ]
            };
        
            chart.setOption(option);
        }
    }
});

this.ckan.module('opendstats-external-stats', function($){
    return {
        initialize: function () {
            var dashboard_url = this.options.url;
            console.log(dashboard_url);
            var ele = $("<iframe></iframe>");
            ele.attr({
                "src": dashboard_url,
                "frameborder": 0,
                "style": "border:0",
                "class": "embed-responsive-item"
            });
            this.el.append(ele);
        }
    }
});