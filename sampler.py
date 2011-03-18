#encoding=utf-8
import urllib
import urllib2
import socket
from SOAPpy import WSDL
from logger import log,log_exce
from datetime import datetime
from SOAPpy import Types

sampler_map = {}
 
def register(name,sampler):
    sampler_map[name] = sampler

def unregister(name):
    del sampler_map[name]

def get_sampler(name):
    return sampler_map[name]

#定义参数异常类
class argsException(Exception):pass

#简单的类型校验
def convert(v=None,t=None):
    if v is None:return None
    elif t.lower()=='string':return str(v)
    elif t.lower() =='int':return int(v)
    elif t.lower() =='float':return float(v)
    elif t.lower()=='bool':
        if v.lower() in ['t','true','y','yes']:
            return True
        else:return False
    else:return str(v)
 
#定义继承BodyType的类型
class argObj(Types.bodyType):pass

# ============ Sampler定义，这些类均不应直接实例化，是被Mixin到Sample类里面使用的 ============

class HTTPSampler(object):

    # 在此判断所需要的信息是否完整
    def is_valid(self):
        return True

    # 采样的逻辑
    def sample(self):
        """
        HTTP 采样的逻辑
        >>> from testcase import Sample,TestCase,TestNode
        >>> test = TestCase()
        >>> sample = Sample(parent=test,type='http',url='http://www.botwave.com',method='GET')
        >>> headers = TestNode(name='headers',parent=sample)
        >>> item = TestNode(name='item',parent=headers)
        >>> item.name = 'User-Agent'
        >>> item.value = 'User-Agent: Mozilla/5.0 (Linux; X11)'
        >>> headers._add_or_append_attr('item',item)
        >>> sample.headers = headers
        >>> data = TestNode(name='data',parent=sample)
        >>> data.kwargs = {'name':'jeff','password':'hello'}
        >>> #sample.data = data
        >>> sample.url
        'http://www.botwave.com'
        >>> sample()
        >>> len(sample._context.items())
        5
        >>> sample._context['code']
        200
        """

        from testcase import TestResult

        log.debug('starting http sample')

        result = TestResult(self._name)
        if self.timeout:
            log.debug('setting request timeout')
            socket.setdefaulttimeout(self.timeout)

        # 开始采样了，开cookies，发送请求，获得响应结果，响应头。
        handlers = []
        # 如果允许Cookies，使用Cookies处理器
        if self._parent.cookies_enable:
            log.debug('enable cookies')
            handlers.append(urllib2.HTTPCookieProcessor())

        log.debug('building url opener')
        opener = urllib2.build_opener(*handlers)


        # 如果显式设置请求头
        if getattr(self,'headers',None):
            log.debug('setting headers')
            opener.addheaders = [(item.name,getattr(item,'value',None) or item._text) for item in self.headers.item]

        # 整理URL及参数
        log.debug('the url is %s'%self.url)
        url = self.url
        data = getattr(self,'data','')
        if data:
            data = urllib.urlencode(data.kwargs)

        if self.method.lower() == 'get':
            if data:
                url = '?'.join((url,data))
        try:
            log.debug('finnally , getting the url %s'%url)

            result.start_time = datetime.now()
            if data:
                response = opener.open(url,data)
            else:
                response = opener.open(url)
            result.end_time = datetime.now()

            # 采样的结果需要暴露5样东西：url,code，msg，responseText,responseHeaders
            
	    result.url = self._parent._context[self.id+'.url'] = self._context['url'] = response.geturl()
            result.code = self._parent._context[self.id+'.code'] = self._context['code'] = response.code
            result.msg = self._parent._context[self.id+'.msg'] = self._context['msg'] = response.msg
            result.responseText = self._parent._context[self.id+'.responseText'] = self._context['responseText'] = response.read()
            result.responseHeaders = self._parent._context[self.id+'.responseHeaders'] = self._context['responseHeaders'] = response.info()
        except:
            result.status = "ERROR"
	    result.code=503
            result.exc_info = log_exce('something wrong')
	result.httpHeader=opener.addheaders
        return result

register('http',HTTPSampler)

class SOAPSampler(object):

    def is_valid(self):
        pass
    #校验并构造soap所需要的参数
    def translate_arg(self,arg,name,o=None,sign=None,k='',l=[]):
        b=True
        if arg.__class__ is not dict:
            return False
        if sign is None:
            te=self.wsdltypes.elements[name]
            c=te.content
        else:
            te=self.wsdltypes.types[name]
            c=te.content
        while c.__class__ not in [tuple,list] and c is not None:
            c=getattr(c,'content',None)
        if c is None:
            return False
        if c.__class__ in [tuple,list] and len(c) == len(arg.keys()):
            for item in c:
	        print '=============it %s==============='%k
                if item.attributes.has_key('name') and item.attributes.has_key('type') and arg.has_key(item.attributes['name']):
                    #k+=item.attributes['name']+'.'
		    if item.attributes['type'][0] ==self.namespace:
		        k+=item.attributes['name']+'.'
                        obj = argObj()
                        d=arg[item.attributes['name']]
                        if o ==None:
                            arg[item.attributes['name']]=obj
                        else:
                            o._addItem(item.attributes['name'], obj)
                        b=self.translate_arg(d,item.attributes['type'][1],obj,'',k)
                    elif Types.bodyType in o.__class__.__bases__:
                        o._addItem("ns1:"+item.attributes['name'],convert(arg[item.attributes['name']],item.attributes['type'][1]))
                else :
		    if len(l)==0:
		        l.append('the args is required but not given,as follow:')
		    if item.attributes.has_key('name') and (not arg.has_key(item.attributes['name'])):
		        #k+=item.attributes['name']+'.'
			l.append(k+item.attributes['name'])
                    #continue
        elif c.__class__ in [tuple,list] and len(c) > len(arg.keys()):
	    l.append('the args given less than required,as follow:')
	    for item in c:
	        if item.attributes.has_key('name') and (not arg.has_key(item.attributes['name'])):
		    #k+=item.attributes['name']+'.'
		    l.append(k[:-1]+item.attributes['name'])
	elif c.__class__ in [tuple,list] and len(c) < len(arg.keys()):
	    attrlist=[]
	    l.append('the args given more than required,as follow:')
	    for item in c:
	        if item.attributes.has_key('name'):
	            attrlist.append(item.attributes['name'])
	    for (k1,v) in arg.items():
	        if k1 not in attrlist:
		    l.append(k+k1) 
        if len(l)>0:
	    b =l
        elif b : 
            b = arg
        return b
    
    #把配置文件中的data转换成对应的json	
    def wrapdata(self):
        if self.data.format == 'json':
	    import json
	    if '\'' in self.data._text:
	        self.data._text=self.data._text.replace('\'','\"')
            self.data.kwargs=json.loads(self.data._text)
	    #build(self.data.kwargs)
         
    # 采样的逻辑
    def sample(self):
        server = WSDL.Proxy(self.wsdl)
        self.namespace = namespace = server.wsdl.targetNamespace
	#设置argObj._validURI值
	argObj._validURIs = (namespace, ) 
	server.methods[self.method].namespace = namespace
        method = getattr(server,self.method)
	self.wsdltypes = server.wsdl.types[namespace]
        from testcase import TestResult
	result = TestResult(self._name)
	server.soapproxy.config.dumpSOAPOut = 1
	server.soapproxy.config.dumpSOAPIn = 1
	try:
	    self.wrapdata()
	    if self.data.kwargs:
                kwargs = self.translate_arg(self.data.kwargs,self.method)
		if kwargs.__class__ is dict:
                    soap_result = method(**kwargs)
		elif kwargs.__class__ is list:
		    print 'method\'s arg error!!!!'
                    error_root='the data._text of the SOAPsample named \''+self.id+'\' in '+self._parent.name+'.xml is error!!!'
                    errormsg=kwargs[0];
		    for item in kwargs[1:]:
		        errormsg+=item+';'
		    raise argsException,error_root+'\n\t\t\t'+errormsg
            else:
                soap_result = method()
	    rs=self.getDataField(soap_result)
            result.soapRespone=self._parent._context[self.id] = self._context[self.id] = rs
	    result.code =200
        except:
	    result.status='ERROR'
	    result.exc_info = log_exce('something wrong')
	
	print 'result\'s status',result.status
	return result
	   
    def getDataField(self,arg):
        if arg.__class__ == Types.structType:
            for item in arg.__dict__.items():
	        if 'element' == item[0]: continue
                if '_'in item[0] : continue
                if 'schema' == item[0]: continue
                if item[1].__class__ is Types.structType:
                    arg = self.getDataField(item[1])
                elif type(item[1]) in (tuple,list):
                    arg = item[1]     
        return arg         
    
register('soap',SOAPSampler)

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)

