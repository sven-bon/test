#encoding=utf-8
import traceback
from logger import log
from xml.dom import minidom


def get_child_tags(xml,tag=None):
    log.debug('getting child tags')
    ret = []
    for node in xml.childNodes:
        if node.__class__ == minidom.Element:
            if not tag:
                ret.append(node)
            elif node.tagName == tag:
                ret.append(node)
    return ret
 
#result生成xml
def create_xmldoc(result):
    xml_doc = minidom.Document()
    testResult=xml_doc.createElement("testResult")
    testResult.setAttribute("name",result.nodename)
    testResult.setAttribute("status",result.status)
    testResult.setAttribute("start_time",str(result.start_time))
    testResult.setAttribute("end_time",str(result.end_time))
    testResult.setAttribute("time_use",str(result.end_time-result.start_time))
    for rs in result.sections:
        child=xml_doc.createElement(rs.nodetype)
        #sample的结果
        if rs.nodetype in [u'sample','sample']: 
            child.setAttribute('id',rs._sample.id)
	    if getattr(rs._sample,'url',None):
	        child.setAttribute('url',rs._sample.url)
	    if getattr(rs._sample,'wsdl',None):
	        child.setAttribute('wsdl',rs._sample.wsdl)
	    child.setAttribute('method',rs._sample.method)
	    if getattr(rs,'code',None):
	        child.setAttribute('code',str(rs.code))
            child.setAttribute('status',rs.status)    

        else:   #assert的结果
	    child.setAttribute('status',rs.status)
            if rs._assert.__dict__.has_key('type'):
                child.setAttribute('type',rs._assert.type)
	        if rs._assert.__dict__.has_key('item'):
	            args = [item._text for item in rs._assert.item]
		    exp = rs._assert.type+'['
		    for i in args:
		        exp+=i+','
		    exp = exp[:-1]+']'
                    child.setAttribute('expression',exp)
        if rs.status in ['ERROR','FAIL'] or getattr(rs,'log',None): #如果发生异常
            #打印soap_result
	    if getattr(rs,'soapRespone',None):
	        from SOAPpy import Types
		child_rs_soap = xml_doc.createElement('soap_Result')
		if type(rs.soapRespone) in [tuple,list]:
		    child_rs_soap_attr= xml_doc.createElement("list")
		    for item in rs.soapRespone:
		        if item.__class__ is Types.structType:
			    child_rs_soap_attr.setAttribute('name',item._name)
			    child_rs_soap_attr_list= xml_doc.createElement("attribute")
			    for i in item.__dict__.items():
			        if '_' not in i[0]:
			            child_rs_soap_attr_list.setAttribute(i[0],i[1])
			    child_rs_soap_attr.appendChild(child_rs_soap_attr_list)
			else:
                            child_rs_soap_text = xml_doc.createTextNode(item)
                            child_rs_soap.appendChild(child_rs_soap_text)
		    child_rs_soap.appendChild( child_rs_soap_attr)
		elif rs.soapRespone.__class__ is Types.structType:
		    child_rs_soap_attr= xml_doc.createElement("attribute")
		    child_rs_soap_attr.setAttribute('name',rs.soapRespone._name)
		    child_rs_soap_attr.setAttribute('type',rs.soapRespone.__class__)
		    for item in rs.soapRespone.__dict__.items():
                        child_rs_soap_attr.setAttribute(item[0],str(item[1]))
		    child_rs_soap.appendChild( child_rs_soap_attr)
	        else:
		    child_rs_soap_text = xml_doc.createTextNode(str(rs.soapRespone))
                    child_rs_soap.appendChild(child_rs_soap_text)
		child.appendChild(child_rs_soap)

	    if rs.__dict__.has_key('httpHeader'):
                child_rs_httpheader = xml_doc.createElement('httpHeader')
		for item in rs.httpHeader:
		    child_rs_httpheader_attr= xml_doc.createElement("attribute")
		    child_rs_httpheader_attr.setAttribute('name',item[0])
                    child_rs_httpheader_attr.setAttribute('value',item[1])
                    child_rs_httpheader.appendChild(child_rs_httpheader_attr)
                child.appendChild(child_rs_httpheader)
            if rs.__dict__.has_key('responseHeaders'):
                child_rs_resheader = xml_doc.createElement('responseHeader')
		for rsitem in rs.responseHeaders.__dict__.items():
		    child_rs_resheader_attr= xml_doc.createElement("attribute")
		    child_rs_resheader_attr.setAttribute('name',str(rsitem[0]))
		    if type(rsitem[1]) is list:
			for i in rsitem[1]:
			    if ':' in i:
		                child_rs_resheader_attr_list= xml_doc.createElement("key")
                                key=i[:i.index(':')]
				value=i[i.index(':')+1:]
			        child_rs_resheader_attr_list.setAttribute(key,value)
                                child_rs_resheader_attr.appendChild(child_rs_resheader_attr_list)
		    elif type(rsitem[1]) is dict:
		        for i in rsitem[1].items():
		            child_rs_resheader_attr_list= xml_doc.createElement("key")				
			    child_rs_resheader_attr_list.setAttribute(i[0],i[1])
                            child_rs_resheader_attr.appendChild(child_rs_resheader_attr_list)
                    else:
		        child_rs_resheader_attr.setAttribute('value',str(rsitem[1]))
                    child_rs_resheader.appendChild(child_rs_resheader_attr)
                #child_rs_resheader_text = xml_doc.createTextNode(str(rs.responseHeaders))
                #child_rs_resheader.appendChild(child_rs_resheader_text)
                child.appendChild(child_rs_resheader)
            
	    if rs.__dict__.has_key('responseText'):
		def getCharset():
		    content_type=rs.responseHeaders.dict['content-type']
		    charsets=content_type.split(';')
		    for item in charsets:
		        if 'charset=' in item:
			    if 'gb' in item.lower():
			        return 'gbk'
			    else:
			        return item[item.index('=')+1:]
		charset =getCharset()
                child_rs_resText = xml_doc.createElement('responseText')
		data = rs.responseText.decode(charset)
		if ']]>' in data:
		    data = data.replace(']]>',']] >')
                child_rs_resText_text = xml_doc.createCDATASection(data)
                child_rs_resText.appendChild(child_rs_resText_text)
                child.appendChild(child_rs_resText)
	    
	    if rs.status in ['ERROR'] or rs.__dict__.has_key('exc_info'):
                child_rs_except=xml_doc.createElement('exception')
                child_rs_except_text1=xml_doc.createTextNode('ERROR: %s '%str(rs.exc_info[0]).replace('<','').replace('>',''))
                child_rs_except.appendChild(child_rs_except_text1)
	        child_rs_except_text2=xml_doc.createTextNode('ERROR: %s'%rs.exc_info[1].message)
                child_rs_except.appendChild(child_rs_except_text2)
                child_rs_except_textmsg=xml_doc.createTextNode('More Information:')
                child_rs_except.appendChild(child_rs_except_textmsg)
	        for filename, lineno, function, msg in traceback.extract_tb(rs.exc_info[2]):
	            child_rs_except_text3=xml_doc.createTextNode('%s line %s in %s function [%s]'%(filename,lineno,function,msg))
	            child_rs_except.appendChild(child_rs_except_text3)
                child.appendChild(child_rs_except)
	    
        testResult.appendChild(child)
    
    if result.__dict__.has_key('exc_info'):
        rs_except=xml_doc.createElement('exception')
        rs_except_text1=xml_doc.createTextNode('ERROR: %s'%str(result.exc_info[0]).replace('<','').replace('>',''))
        rs_except.appendChild(rs_except_text1)
	rs_except_text2=xml_doc.createTextNode('ERROR: %s'%result.exc_info[1].message)
        rs_except.appendChild(rs_except_text2)
        rs_except_textmsg=xml_doc.createTextNode('More Information:')
        rs_except.appendChild(rs_except_textmsg)
	for filename, lineno, function, msg in traceback.extract_tb(result.exc_info[2]):
	    rs_except_text3=xml_doc.createTextNode('%s line %s in %s function (%s)'%(filename,lineno,function,msg))
	    rs_except.appendChild(rs_except_text3)
        testResult.appendChild(rs_except)
    
    xml_doc.appendChild(testResult)
    #return encode_for_xml(xml_doc.toxml(),'utf-8')
    return xml_doc



