from django.shortcuts import render,HttpResponse
from all_models.models import *
from apps.common.func.WebFunc import *
import openpyxl,xlrd,json,platform
from django.http import StreamingHttpResponse
from apps.common.model.ExcelRead import *


def uiTestPage(request):
    context = {}
    return render(request,"ui_test/ui_file/ui_file.html",context)

def userIsFileShowSubPage(request):
    userDir = "%s/%s/%s" % (BASE_DIR.replace("\\", "/"),"ui_file_uploads",request.session.get("loginName"))
    if not os.path.exists(userDir):
        #没有用户的文件夹，显示大按钮

        return HttpResponse(ApiReturn(code=100000).toJson())
    else:
        for root, dirs, files in os.walk(userDir):
            if files == []:
                return HttpResponse(ApiReturn(code=100000).toJson())
        return HttpResponse(ApiReturn().toJson())

def createDir(request):
    userDir = "%s/%s/%s" % (BASE_DIR.replace("\\", "/"), "ui_file_uploads", request.session.get("loginName"))
    if not os.path.exists(userDir):
        os.makedirs(userDir)
    return HttpResponse(ApiReturn().toJson())


def fileExists(request):
    try:
        fileDict = request.FILES
    except Exception as e:
        return HttpResponse(ApiReturn(ApiReturn.CODE_WARNING, message="未检测到文件").toJson())
    userDir = "%s/%s/%s/%s" % (
    BASE_DIR.replace("\\", "/"), "ui_file_uploads", request.session.get("loginName"), fileDict["file"])

    if os.path.exists(userDir):
        return HttpResponse(ApiReturn(code=100000).toJson())
    else:
        return HttpResponse(ApiReturn().toJson())

def fileUpload(request):
    fileDict = request.FILES
    if fileDict == {}:
        return HttpResponse(ApiReturn(ApiReturn.CODE_WARNING, message="未检测到文件").toJson())
    userDir = "%s/%s/%s/%s" % (BASE_DIR.replace("\\", "/"), "ui_file_uploads", request.session.get("loginName"),fileDict["file"])
    if os.path.exists(userDir):
        os.remove(userDir)
    destination = open(os.path.join(userDir), "wb+")
    for chunk in fileDict["file"].chunks():
        destination.write(chunk)
    destination.close()

    return HttpResponse(ApiReturn().toJson())

def checkFileList(request):
    userDir = "%s/%s/" % (BASE_DIR.replace("\\", "/"), "ui_file_uploads")
    excelFilesDict = {}
    context = {}

    allUserDir = []
    # 有用户的文件夹
    for filename in os.listdir(userDir):
        if os.path.isdir("%s%s" % (userDir,filename)):
            if filename == request.session.get("loginName"):
                excelFilesDict[filename] = {"userName":request.session.get("userName"),"sheet":{}}
            else:
                excelFilesDict[filename] = {"userName":TbUser.objects.get(loginName=filename).userName,"sheet":{}}
            userFileList = []
            for excelName in os.listdir("%s%s" % (userDir, filename)):
                print("%s%s/%s" % (userDir, filename, excelName))
                if os.path.isfile("%s%s/%s" % (userDir, filename, excelName)):
                    userFileList.append(excelName)
                    print(excelName)
                    for index in userFileList:
                        excelFilesDict[filename]["sheet"][index] = []
                        fileDir = "%s%s/%s" % (userDir, filename, index)
                        print(fileDir)
                        print(index)
                        fileType = index.split(".")
                        if fileType[1] == "xls":
                            workbook = xlrd.open_workbook(fileDir)
                            sheets = workbook.sheet_names()
                            for i in range(len(sheets)):
                                if "case" in sheets[i].lower():
                                    excelFilesDict[filename]["sheet"][index].append(sheets[i])
                        else:
                            print("##########")
                            print(fileDir)
                            wb = openpyxl.load_workbook(fileDir)
                            sheets = wb.get_sheet_names()
                            for i in range(len(sheets)):
                                sheet = wb.get_sheet_by_name(sheets[i])
                                excelFilesDict[filename]["sheet"][index].append(sheet.title)

    context["excelFilesDict"] = excelFilesDict
    context["loginName"] = request.session.get("loginName")

    return HttpResponse(ApiReturn(body=context).toJson())

def runTest(request):
    httpConfList = json.loads(request.POST.get("httpConfList"))
    fileName = request.POST.get("fileName")
    sheetNameList = json.loads(request.POST.get("sheetNameList"))
    businessLineId = request.POST.get("businessLineId")
    moduleId = request.POST.get("moduleId")
    userName = request.POST.get("userName")
    for httpConfIndex in httpConfList:
        tbModel = TbUITestExecute()
        # 基本信息
        tbModel.fileName = fileName
        tbModel.sheetName = ",".join(sheetNameList)
        tbModel.fileAddBy = userName
        tbModel.httpConfKey = httpConfIndex
        tbModel.businessLineId = businessLineId
        tbModel.moduleId = moduleId
        tbModel.addBy = request.session.get("loginName")
        tbModel.save()
        saveId = tbModel.id
        tcpStr = '{"do":5,"UITaskExecuteId":"%s"}' % saveId
        print(tcpStr)
        retApiResult = send_tcp_request_to_uiport(tcpStr)
        if retApiResult.code != ApiReturn.CODE_OK:
            tbModel.execStatus = 4
            tbModel.testResult = "EXCEPTION"
            print(str(retApiResult.code)+":"+retApiResult.message)
            tbModel.testResultMessage = str(retApiResult.code)+":"+retApiResult.message
            tbModel.save()
            addUserLog(request, "单接口管理->接口调试->发送TCP请求->失败，原因\n%s" % retApiResult.toJson(), "FAIL")
            return HttpResponse(retApiResult.toJson(ApiReturn.CODE_WARNING))
        else:
            addUserLog(request, "单接口管理->接口调试->发送TCP请求->成功", "PASS")
            return HttpResponse(ApiReturn(ApiReturn.CODE_OK).toJson())

def file_download(request):
    userDir = "%s/%s/" % (BASE_DIR.replace("\\", "/"), "ui_file_uploads")
    file_name = "%s%s/%s" % (userDir,request.GET.get("loginName"),request.GET.get("fileName"))

    def file_iterator(file_name, chunk_size=512):  # 用于形成二进制数据
        with open(file_name, 'rb') as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    the_file_name = file_name  # 要下载的文件路径
    response = StreamingHttpResponse(file_iterator(the_file_name))  # 这里创建返回
    response['Content-Type'] = 'application/vnd.ms-excel'  # 注意格式
    print(request.GET.get("fileName"))
    response['Content-Disposition'] = 'attachment;filename="%s"' % request.GET.get("fileName")  # 注意filename 这个是下载后的名字
    return response

def file_delete(request):
    userDir = "%s/%s/" % (BASE_DIR.replace("\\", "/"), "ui_file_uploads")
    file_name = "%s%s/%s" % (userDir, request.POST.get("loginName"), request.POST.get("fileName"))
    os.remove(file_name)
    return HttpResponse(ApiReturn().toJson())