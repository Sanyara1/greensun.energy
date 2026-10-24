# Ноябрь 2026 — редакционный кандидат V6
Версия: 6.0 от 24.10.2026 (Europe/Moscow).
Статус: EDITORIAL_DRAFT_NOT_DEPLOYED. Подготовлено ассистентом; модельное ревью и согласование владельцем этой версии не выполнены. Не является исполняемым планом factory.py.
Основание: решение владельца продолжить переработку 12 оставшихся постов под развитие цифрового инженера.

## Состояние и сохранение опубликованного
Владелец передал успешный вывод CHANNEL_POST_SENT и подтвердил просмотр https://t.me/Gsun_ai/4.
Опубликован пост id=2026-11-02 («Проект станции — это ещё и план её обслуживания»), ранее scheduled_at=2026-11-04T11:00:00+03:00. Не изменять его RU/EN, media_id, исходную дату или запись post:2026-11-02:-1004428833073 в deliveries.sqlite. Не планировать замену на освободившийся день автоматически.
Исходный sealed hash пакета: 01d37563a58fcb38d876f57084e80f86f65bc42d862292ca0318ae3761d87266.
Последняя сообщённая конфигурация: оба флага генерации/публикации no; оба таймера inactive; bridge active. Это переданный результат проверки, не независимый доступ к VPS.
Точное содержимое остальных 12 RU/EN постов получено из экспорта владельца от 24.10.2026. Полного JSON активного плана, фактов и media-каталога в этой сессии нет.

## Основания и границы
S1 — [Развитие GSun и цифрового инженера, 1.0](https://chatgpt.com/space/page_8ec26c6986b8819186c99629d3ae25b1), прочитано 24.10.2026: цели, read-only старт, этапы, испытания, редакционная политика. Это согласованное направление, не доказательство реализации.
S2 — [Рабочее место станции](https://github.com/GSun-Energy/gsun-ai-platform/blob/aa52527400ce350f17b500d3538f5cff30fa7e63/docs/product/STATION_WORKSPACE_2026-10-21_RU.md): реализация пилота, исправления графиков, пропуски, семантика баланса. Физическая причина спорных каналов не установлена; расчётные нагрузка/импорт не становятся независимыми измерениями.
S3 — [Паспорт Kristal](https://github.com/GSun-Energy/gsun-ai-platform/blob/aa52527400ce350f17b500d3538f5cff30fa7e63/docs/station-passport-pilot-2026-10-21.md): структурированный паспорт, неизвестные поля; загрузка документов и расширенное редактирование не реализованы в этом изменении.
S4 — [Отчёты](https://github.com/GSun-Energy/gsun-ai-platform/blob/aa52527400ce350f17b500d3538f5cff30fa7e63/docs/station-grid-reports-2026-10-21.md): JSON/CSV, проверка доступа, происхождение и ограничения; мобильная приёмка остаётся.
S5 — [Автономность](https://github.com/GSun-Energy/gsun-ai-platform/blob/aa52527400ce350f17b500d3538f5cff30fa7e63/docs/architecture/AUTONOMY_PATH_2026-10-20_RU.md): архитектурный план, облачный backend действующий, локальная модель не доказывает автономность всего приложения.
S6 — экспорт действующего V5 владельцем: сохраняются id=2026-11-04 и id=2026-11-06, даты 9 и 13 ноября. Существующие fact_ids указаны в разделах ниже; их актуальность нужно сверить с VPS.
S7 — требование владельца о будущих API-пулах из этой беседы; реализация не подтверждена S2/S5.
S8 — [Точка продолжения фабрики](https://github.com/Sanyara1/greensun.energy/blob/f9c554914cab1911c862375c1a6a58f7ca96269b/communications/checkpoints/2026-10-24-PR_FACTORY_RESUME_RU.md).
Все GitHub-основания служат внутренней редакционной проверке. Не вставлять приватные ссылки в публичные подписи. Перед выпуском повторно проверить актуальность статусов и разрешение раскрытия скриншотов/клиентских данных.

## 02.11, 11:00 — id=2026-11-01
Решение: доработать. Статус утверждений: НАПРАВЛЕНИЕ. Основание S1.
RU:
Зачем GSun создаёт цифрового инженера?

Владельцу станции нужен понятный ответ: что показывают данные, откуда взялся вывод и что стоит проверить дальше.

Мы развиваем помощника, который связывает вопрос с документами и данными конкретного объекта. Начальный режим — чтение и объяснение. Если сведений недостаточно, это должно быть видно в ответе.

Это направление разработки GSun. Его готовность будем показывать через конкретные проверки.

EN:
Why is GSun developing a digital engineer?

A site owner needs a clear answer: what the data shows, what supports the conclusion and what to check next.

We are developing an assistant that connects a question with documents and data from the specific site. The initial mode is reading and explanation. When evidence is insufficient, the answer should make that clear.

This is GSun’s development direction. We will demonstrate progress through specific checks.

Визуал: новая карточка «Вопрос → источник → объяснение». Пометка «Направление развития». Без изображения готового интерфейса.
Условие выпуска: проверить, что формулировка остаётся целевым направлением.

## 06.11, 11:00 — id=2026-11-03
Решение: заменить. Статус: РЕАЛИЗОВАНО В ПИЛОТЕ, ограниченная область. Основание S2.
RU:
Как связать график станции с вопросом инженеру?

В пилоте GSun.AI для Hotel Kristal реализован переход от выбранного дня на графике к черновику вопроса в чате. Контекст станции и даты сохраняется; отправку запускает пользователь.

Так можно обсуждать конкретный период работы объекта. Сам график ещё не устанавливает причину отклонения — для этого нужны подходящие измерения и проверка гипотез.

EN:
How can a station chart become an engineering question?

In the GSun.AI pilot for Hotel Kristal, the selected chart day can be carried into a draft chat question. The station and date stay in context; the user sends the question.

This makes it possible to discuss a specific operating period. The chart alone does not establish the cause of a deviation: suitable measurements and hypothesis testing are still needed.

Визуал: реальный разрешённый скриншот перехода; скрыть аккаунт, личную историю и идентификаторы. Альтернатива — явно обозначенная схема процесса.
Условие выпуска: подтвердить актуальную работу перехода и разрешение на раскрытие выбранного изображения. Не выдавать прошлую проверку за ноябрьский релиз.

## 09.11, 11:00 — id=2026-11-04
Решение: оставить RU/EN и существующую карточку без изменений. Основания S6: GSUN_WEB_SERVICES, GSUN_WEB_MONITORING, GSUN_WEB_CONTACT.
RU:
Солнечная станция уже установлена?

В GSun можно обратиться и с действующим объектом. Мы предлагаем обслуживание солнечных электростанций и обсуждаем задачи мониторинга: выработку, нагрузку и состояние оборудования.

Обсудить ваш объект: ceo@gsun.io

Иллюстрация: редакционная карточка GSun.

EN:
Already have a solar installation?

You can contact GSun about an existing site. We offer maintenance for solar installations and discuss monitoring needs: generation, load and equipment condition.

Discuss your site with us: ceo@gsun.io

Illustration: GSun editorial card (Russian).

Визуал: сохранить card-ru-2026-11-04-605d57441eac. Условие: проверить файл/hash и актуальность исходных фактов.

## 11.11, 11:00 — id=2026-11-05
Решение: доработать. Статус: РЕАЛИЗОВАНО В ПИЛОТЕ. Основание S2.
RU:
Пропуск на графике — тоже информация.

В пилоте GSun.AI интервалы между точками больше 15 минут обозначаются отдельно. Линия не достраивается через такой разрыв, а отсутствующие значения не превращаются в нули.

Это помогает увидеть границу доступных данных. По одному пропуску нельзя заключить, что станция остановилась: сначала нужно выяснить, где потерялись измерения — при сборе, передаче или выдаче.

EN:
A gap in a chart carries information too.

In the GSun.AI pilot, intervals longer than 15 minutes between points are marked separately. The line is not extended across the gap, and missing values are not turned into zeros.

This shows the limits of the available data. A gap alone does not prove the station stopped: the next step is to determine whether measurements were lost during collection, transfer or retrieval.

Визуал: разрешённый исторический скриншот с датой и пометкой «архив пилота». Не рисовать вымышленную телеметрию. Изменена первоначальная тема «генерация/нагрузка»: семантика каналов ещё требует проверки; тема пропусков имеет более надёжное основание.
Условие: визуально сверить разрыв с выбранным исходным рядом.

## 13.11, 11:00 — id=2026-11-06
Решение: оставить RU/EN и карточку. Основания S6: GSUN_WEB_SERVICES, GSUN_WEB_CONTACT.
RU:
Нужно обратиться по обслуживанию станции? Попробуйте описать задачу в трёх строках:

• Что вы заметили?
• Когда это началось?
• Повторяется ли ситуация?

Запишите наблюдения своими словами — готовый диагноз не нужен. Это подсказка для обращения, а не инструкция по ремонту.

GSun обслуживает солнечные электростанции. Контакт: ceo@gsun.io

Иллюстрация: редакционная карточка GSun.

EN:
Need to contact someone about solar installation maintenance? Try describing the issue in three lines:

• What did you notice?
• When did it start?
• Does it happen repeatedly?

Describe your observations in your own words — no diagnosis is needed. This is a guide to making an enquiry, not repair instructions.

GSun provides maintenance for solar installations. Contact: ceo@gsun.io

Illustration: GSun editorial card (Russian).

Визуал: сохранить card-ru-2026-11-06-3c8e8b9c4150. Условие: проверить файл/hash и исходные факты.

## 16.11, 11:00 — id=2026-11-07
Решение: заменить. Статус: РЕАЛИЗОВАНО В ПИЛОТЕ. Основание S3.
RU:
Паспорт станции: полезно видеть и незаполненные поля.

В пилоте GSun сведения об объекте, оборудовании, солнечных панелях и источниках измерений сгруппированы в отдельные разделы паспорта. Неизвестные сведения остаются незаполненными.

Так инженер видит, на какие данные можно опереться и что нужно уточнить. Наличие раздела документов пока не означает, что их загрузка уже доступна.

EN:
A station passport should show what is still unknown.

In the GSun pilot, site details, equipment, solar-panel information and measurement sources are grouped into separate passport sections. Unknown information remains unfilled.

This helps an engineer see what can support an assessment and what still needs clarification. A documents section does not yet mean document uploads are available.

Визуал: обезличенный актуальный паспорт с неизвестным полем; не добавлять фиктивных документов. Условие: проверить текущие возможности перед выпуском.

## 18.11, 11:00 — id=2026-11-08
Решение: заменить. Статус: ПЛАН ПРОВЕРКИ. Основание S1.
RU:
Как будем проверять ответы цифрового инженера?

До испытания задаём вопросы, источники и ожидаемые ответы. Затем проверяем числа, единицы измерения, выбранный объект и поведение при нехватке данных.

Важен и отказ от необоснованного вывода. Уверенный ответ без подходящего источника не считаем успешным.

Это принятый подход к дальнейшим испытаниям GSun. Результаты каждого прогона будем показывать отдельно.

EN:
How will we test the digital engineer’s answers?

Before a trial, we define questions, sources and expected answers. We then check numbers, units, the selected site and behaviour when information is missing.

Declining an unsupported conclusion matters too. A confident answer without a suitable source does not count as success.

This is GSun’s agreed approach to future trials. Results from each run will be reported separately.

Визуал: новая карточка «Источник / Числа / Объект / Недостаток данных», пометка «План испытаний». Условие: не добавлять выдуманный процент точности.

## 20.11, 11:00 — id=2026-11-09
Решение: заменить. Статус: АРХИТЕКТУРНЫЙ ПЛАН. Основания S1, S5.
RU:
Локальная модель — один шаг к автономному помощнику.

Для работы цифрового инженера без облака нужны также доступ к разрешённым данным, проверка прав и сохранение истории.

В GSun планируем проверять этот путь целиком: качество ответов, задержку, восстановление после потери связи. Работа модели на отдельном компьютере ещё не доказывает автономность всей платформы.

EN:
A local model is one step towards an autonomous assistant.

For a digital engineer to work without the cloud, it also needs access to authorised data, permission checks and conversation history.

At GSun, we plan to test that complete path: answer quality, latency and recovery after a connection loss. Running a model on one computer does not yet prove the whole platform is autonomous.

Визуал: схема «Модель + данные + права + история», пометка «План». Условие: проверить статус автономного прогона; не обещать уже работающий offline.

## 23.11, 11:00 — id=2026-11-10
Решение: доработать. Статус: РЕАЛИЗОВАНО В ПИЛОТЕ, не независимая проверка данных. Основание S4.
RU:
Отчёт полезен, когда понятно происхождение чисел.

В пилоте GSun реализованы выбор периода и выгрузка отчёта в JSON/CSV. Доступ проверяется по станции; в экспорте сохраняются сведения об источнике и ограничениях данных.

Это основа для дальнейшего разбора. Сам факт выгрузки не подтверждает точность измерений или прохождение официальной проверки.

EN:
A report is useful when the origin of its numbers is clear.

The GSun pilot implements period selection and JSON/CSV report export. Access is checked for the station, and exports retain source information and data limitations.

This supports further analysis. An export alone does not establish measurement accuracy or successful official verification.

Визуал: обезличенный фрагмент экспорта с периодом и источником; не показывать демонстрационные MRV/CO₂ значения как результат. Условие: подтвердить выгрузку через действующий кабинет.

## 25.11, 11:00 — id=2026-11-11
Решение: доработать. Статус: ПРИНЦИП ПРОДУКТА; криптографический результат не заявляется. Основание S1 и подтверждённое владельцем направление Oracle; перед технической демонстрацией нужны отдельные доказательства.
RU:
Почему для GSun важна проверяемая история данных?

В направлении Oracle мы ставим задачу сохранять связь показаний с объектом и их происхождением. Подпись данных — часть этой работы.

Для обсуждения сертификатов потребуется отдельно подтвердить измерения, применимую процедуру и отсутствие повторного зачёта одного эффекта. Мы не считаем наличие подписи обещанием автоматической выдачи сертификата.

EN:
Why does a verifiable data history matter to GSun?

Within the Oracle direction, our goal is to preserve the connection between readings, their site and their origin. Data signing is part of that work.

Any discussion of certificates also requires evidence about measurements, the applicable process and prevention of double counting the same effect. We do not treat a signature as a promise of automatic certificate issuance.

Визуал: новая карточка «Происхождение / История / Проверка», без печати сертификации, ГОСТ-знаков и имитации выданного сертификата.
Условие: проверить формулировки по актуальной продуктовой позиции; для утверждений о конкретном алгоритме/испытании добавить первичные доказательства. Это не юридическое описание обязательной процедуры для всех видов сертификатов.

## 27.11, 11:00 — id=2026-11-12
Решение: заменить. Статус: ТРЕБОВАНИЕ / ПЛАН. Основания S7, S2, S5.
RU:
Несколько производителей — одна рабочая среда для инженера.

Для дальнейшего развития GSun рассматриваем объединение разрешённых данных станций через API производителей. Цель — помочь обслуживающей организации видеть свои объекты в одном месте.

Это план, а не объявление готовой интеграции. Для каждого подключения предстоит проверить доступные данные, права, задержку и условия API. Облачное подключение само по себе не обеспечивает автономную работу.

EN:
Several manufacturers, one workspace for the engineer.

For GSun’s further development, we are considering combining authorised station data through manufacturer APIs. The goal is to help service organisations view their sites in one place.

This is a plan, not an announcement of a completed integration. Each connection requires checks of available data, permissions, latency and API terms. A cloud connection alone does not provide autonomous operation.

Визуал: нейтральная схема нескольких станций, пометка «План интеграций»; без логотипов несуществующих партнёров.
Условие: сохранить статус плана, если до выпуска нет доказательств принятой интеграции.

## 30.11, 11:00 — id=2026-11-13
Решение: заменить. Статус: BLOCKED_FUTURE_EVIDENCE. Основание S1.
Это задание редактору, НЕ готовая публичная подпись.
RU — структура: «Итоги ноября: какую задачу выбрали → что изменили → как проверили → что подтверждено → что осталось открытым → следующий шаг».
EN — structure: “November review: the problem selected → the change → how it was tested → confirmed results → open issues → the next step”.
Условие выпуска: реальные результаты ноября и разрешённые к раскрытию материалы, новое RU/EN ревью, одобрение владельца. Никаких заполнителей или обещанных результатов в публикационной очереди.
Резервная законченная подпись, если итог не готов, требует отдельного выбора и согласования:
RU:
Что мы хотим показывать в истории GSun?

Задачу, проверку, результат и следующий шаг. Для нас важно объяснять и достижения, и ограничения — чтобы было понятно, как развивается цифровой инженер.

Планы будем обозначать как планы, а готовые возможности подтверждать конкретными примерами. Так мы хотим вести разговор с клиентами и будущими партнёрами.
EN:
What do we want GSun’s development story to show?

The problem, the test, the result and the next step. We want to explain both achievements and limitations so readers can understand how the digital engineer is developing.

Plans will be labelled as plans, and working capabilities supported by specific examples. This is how we want to communicate with clients and future partners.
Визуал резерва: карточка «Задача → проверка → результат → следующий шаг».

## Проверка и дальнейшая установка
- Две неизменённые подписи сохраняют старую пометку иллюстрации. В новые подписи после выбора ассета добавляется точная пометка иллюстрации/скриншота и язык; проверить итоговый лимит Telegram 1024 UTF-16 units.
- EN тексты соответствуют статусам RU. RU-картинка при EN-подписи должна оставаться явно обозначенной до отдельного подключения EN-медиа.
- Здесь 12 редакционных позиций; опубликованный id02 не включён в заменяемые записи. id не является датой scheduled_at.
- Новые S1–S7 не являются автоматически зарегистрированными fact_ids VPS. Нельзя записать эти посты в активную очередь с прежними GSUN_WEB_* основаниями.
- revise-v2.py в текущей схеме вызывает no_deliveries() для всего месяца и требует media_id=null. После публичной отправки он должен остановиться STOP_EXISTING_DELIVERY_RECORD. Не удалять квитанцию, не обходить этот запрет ручной подменой.
- Перед установкой нужен точный экспорт активного plan/facts/media и ограниченная доработка редактора: замороженные отправленные записи и их receipt сохраняются; изменения разрешены только неотправленным постам; sending_or_unknown блокирует действие; повторная сверка под lock перед записью; backup/readback; новая проверка фактов/медиа и approval=null. Нужны регрессии сохранения отправленного, конкурентной отправки и отказа ревью. Это план доработки, не реализованная функция.
- Напоминания в текущем tick() проверяются отдельно от статуса отправленного поста: досрочно опубликованный id02 может получить напоминание. До включения таймера исправить пропуск напоминаний для sent и определить поведение при unknown. Не создавать фиктивные квитанции напоминаний.
- Сейчас никаких изменений VPS, фактов, плана, карточек, таймеров, инженерного WORK_FOCUS и публикаций не производится.
