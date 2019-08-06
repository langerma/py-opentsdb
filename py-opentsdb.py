import requests
import pandas

try:
    # Use ujson if available.
    import ujson as json
except Exception:
    import json

class OpenTSDBResponseSerie(object):
    """
        A single OpenTSDB response serie i.e 1 element of the response
        array.
        Params:
            **kwargs : OpenTSDB response serie data
    """
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @property
    def id(self):
        """
            id for serie
            Returns:
                metric{sorted=tag,key=value}
        """
        if len(self.tags.keys()) > 0:
            tags = ",".join(["%s=%s" %
                (k, self.tags[k]) for k in sorted(self.tags.keys())])
            return "%s{%s}" % (self.metric, tags)
        else:
            return self.metric


    def alias(self, functOrStr):
        """
            User specified alias using lambda functions and string formatting using
            metadata provided by opentsdb.
            This function fails silently.
            Params:
                functOrStr :    lambda function or python string format. When using lambda
                                functions,  they must begin with '!' e.g. !lambda x: x....
            Return:
                Formatted alias on success and id or failure.
        """
        flatData = self.__flattenedMetadata()
        # Normalized alias
        _alias = ""
        if functOrStr.startswith("!"):
            try:
                _alias = eval(functOrStr[1:])(flatData)
            except Exception as e:
                pass
        else:
            try:
                _alias = functOrStr % (flatData)
            except Exception as e:
                pass

        if _alias == "":
            return self.id

        return _alias


    def __flattenedMetadata(self):
        """
            Flattens all metadata which is used for normalization
        """
        return dict([("metric", self.metric)] +
            [("tags.%s" % (k), v) for k, v in self.tags.items()])

    def datapoints(self, convertTime=False):
        """
            Converts datapoints
            Params:
                convertTime : Whether to convert epoch to pandas datetime
            Return:
                Array of tuples (time, value)
        """
        if convertTime:
            return dict([(pandas.to_datetime(int(k), unit='s'), v) for k, v in self.dps.items()])

        return dict([(int(k), v) for k, v in self.dps.items()])


class OpenTSDBResponse(object):
    """ Complete OpenTSDB response """

    def __init__(self, otsdbResp):
        """
            Params:
                otsdbResp : raw opentsdb response as a str, list or tuple.
        """
        if isinstance(otsdbResp, str) or isinstance(otsdbResp, unicode):
            # string response
            self._series = [ OpenTSDBResponseSerie(**s) for s in json.loads(otsdbResp) ]
        elif isinstance(otsdbResp, list) or isinstance(otsdbResp, tuple):
            # dict response
            self._series = [ OpenTSDBResponseSerie(**s) for s in otsdbResp ]
        else:
            raise RuntimeError("Invalid type: %s" % (type(otsdbResp)))


    @property
    def series(self):
        """
            Use iterator for better memory management
        """
        for s in self._series:
            yield s


    def DataFrame(self, aliasTransform=None, convertTime=False):
        """
            Converts an OpenTSDB array response into a DataFrame
            Params:
                convertTime : Whether to convert epoch to pandas datetime
                aliasTransform : lambda function or string format to customize
                                 serie name i.e. alias
            Return:
                OpenTSDB response DataFrame
        """
        if aliasTransform == None:
            return pandas.DataFrame(dict([
                (s.id, s.datapoints(convertTime)) for s in self.series ]))
        else:
            return pandas.DataFrame(dict([
                (s.alias(aliasTransform), s.datapoints(convertTime)) for s in self.series ]))

class BaseClient(object):

    def __init__(self, host, port=4242, ssl=False):
        if ssl:
            self.url = "https://%s:%d" % (host, port)
        else:
            self.url = "http://%s:%d" % (host, port)

    def queryUrl(self, **kwargs):
        return str("%s/api/query?%s" % (self.url, self.__urlEncodedParams(**kwargs)))

    def __urlEncodedParams(self, aggr="sum", rate=False, counter=False, end=None, **kwargs):

        timeStr = "start=%s" % (kwargs["start"])
        if end != None:
            timeStr += "&end=%s" % (end)

        if rate:
            prefix = "%s:rate:%s" % (aggr, kwargs["metric"])
        elif counter:
            prefix = "%s:rate{counter,,1}:%s" % (aggr, kwargs["metric"])
        else:
            prefix = "%s:%s" % (aggr, kwargs["metric"])

        # TODO: check
        tagsStr = ",".join([ "%s=%s" % (k, kwargs["tags"][k]) for k in sorted(kwargs["tags"].keys()) ])

        if tagsStr != "":
            return "%s&m=%s{%s}" % (timeStr, prefix, tagsStr)
        else:
            return "%s&m=%s" % (timeStr, prefix)

class Client(BaseClient):

    def query(self, **kwargs):
        resp = requests.get(self.queryUrl(**kwargs))
        if resp.status_code >= 200 and resp.status_code < 400:
            return OpenTSDBResponse(resp.text)
            #return resp.text
        # error
        return resp.text
