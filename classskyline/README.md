
# How To Run classskyline

1. install all dependencies

    $ pip install -r requirements/base.txt

2. initial database

    $ python manage.py migrate

3. start server

    $ python manage.py 0.0.0.0:80

# How To Contribute Code

1. 点击网页右上角的 Fork 按钮，Fork 该项目到自己账户的 namespace 下

2. 克隆 Fork 出来的项目（应该在自己的 namespace 中，比如下面的 g11008）

    $> git clone 

3. 修改内容后提交，然后在网页上点击 New Merge Request 按钮，发起一个 Merge 请求

4. Merge 请求发起后，等待合并即可

# How To Update Code From Upstream

1. 添加一个远程仓库

    $> git remote add upstream 

2. 从 upstream 更新代码

    $> git pull upstream master


# Create MySQL Database

    mysql> CREATE DATABASE classskyline CHARACTER SET utf8 COLLATE utf8_general_ci;
