# 事务接口

`pythonboot.transaction` 提供与数据库无关的 Spring 风格事务契约。
框架内置应用级 `TransactionInterceptor`，自动增强容器 Bean 上的事务方法。
数据库 Starter 或应用需要提供具体事务管理器 Bean，框架不创建数据库连接。

```python
from pythonboot import Isolation, Propagation, transactional


class OrderService:
    @transactional(
        propagation=Propagation.REQUIRED,
        isolation=Isolation.READ_COMMITTED,
        timeout=30,
        rollback_for=(Exception,),
        no_rollback_for=(ValueError,),
        transaction_manager="orderTransactionManager",
    )
    async def create_order(self) -> None:
        ...
```

支持 `@transactional`、`@transactional()` 和带参数形式；装饰器不包装方法，
保留原始签名和同步／异步类型。通过 `get_transaction_attribute(method)` 读取
`TransactionAttribute`，通过 `@around(transactional)` 匹配事务方法。
`transaction_manager` 为可选的管理器 Bean 名称，由拦截器解析。

## AOP 执行

同步方法按类型解析 `PlatformTransactionManager`；异步方法通过容器的
`aget_bean` 解析并初始化 `AsyncPlatformTransactionManager`。
未指定管理器名称时使用容器的类型匹配及 primary 规则；指定名称时同时
校验类型。缺失或歧义管理器直接报错，不执行目标方法。

拦截器在业务通知外层调用 `get_transaction`，正常返回后调用 `commit`；
业务异常按回滚规则调用 `rollback` 或 `commit` 后重新抛出原异常。
完成操作失败时抛出完成异常并保留原业务异常链，不重复执行完成操作；
管理器负责完成失败时的资源清理。事务未显式命名时使用方法全限定名。
取消异常也进入回滚流程，取消期间的资源清理由异步管理器保证。

不需要手动声明切面或扫描框架包，直接使用 `@transactional` 即可。
只有通过容器 Bean 代理调用才会增强；实例内部 `self.method()` 自调用、
直接实例化对象、静态方法、类方法、私有方法及生命周期回调不增强。
事务方法不支持生成器或异步生成器；传播、挂起、保存点和 rollback-only
由具体管理器实现，拦截器统一负责事务作用域的开始和完成。

## 管理器契约

同步 Starter 实现 `PlatformTransactionManager`，异步 Starter 实现
`AsyncPlatformTransactionManager`，提供 `get_transaction(definition)`、
`commit(status)` 和 `rollback(status)`。异步接口使用 `await`。
`definition=None` 表示默认事务定义；`timeout=-1` 表示使用管理器默认超时，
其他值以秒计。`read_only` 为资源优化提示，不保证禁止写入。

`TransactionStatus` 描述是否存在物理事务、是否新建事务、是否使用保存点、
是否只可回滚以及是否已完成；可调用 `set_rollback_only()` 标记回滚。
保存点能力单独通过 `SavepointManager` 或 `AsyncSavepointManager` 实现。

| 传播行为 | 管理器行为 |
| --- | --- |
| REQUIRED | 存在事务则加入，否则新建 |
| SUPPORTS | 存在事务则加入，否则无事务执行 |
| MANDATORY | 必须存在事务，否则报错 |
| REQUIRES_NEW | 挂起已有事务，新建独立事务 |
| NOT_SUPPORTED | 挂起已有事务，无事务执行 |
| NEVER | 必须不存在事务，否则报错 |
| NESTED | 已有事务内建立保存点，否则新建事务 |

隔离级别包含 DEFAULT、READ_UNCOMMITTED、READ_COMMITTED、REPEATABLE_READ、
SERIALIZABLE。具体资源不支持的传播行为、隔离级别或保存点能力必须明确报错。

内层参与事务的作用域不独立提交；内层回滚标记共享事务 rollback-only，
外层尝试提交时回滚并抛出 `UnexpectedRollbackError`。
保存点作用域失败应回滚到保存点；独立事务完成后恢复被挂起的上下文。
管理器必须校验状态所属管理器和完成状态，防止重复提交或回滚，
在完成失败或任务取消时释放所拥有的资源并恢复上下文。
异步管理器须防止独立并发任务共享不可并发使用的数据库 Session。

## 回滚规则

`TransactionAttribute.rollback_on(error)` 默认对所有 `Exception` 回滚。
Python 不采用 Java 的受检异常区分；通过 `rollback_for` 和 `no_rollback_for`
显式设置规则。异常继承链中更具体的规则优先，同等匹配时不回滚规则优先；
无规则匹配时不回滚。取消、系统退出等非 `Exception` 的 `BaseException` 总是回滚。
